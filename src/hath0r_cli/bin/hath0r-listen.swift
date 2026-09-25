import AVFoundation
import Foundation
import Speech

class AudioListener: NSObject {
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    private let audioEngine = AVAudioEngine()
    private var recognitionRequest: SFSpeechAudioBufferRecognitionRequest?
    private var recognitionTask: SFSpeechRecognitionTask?
    private var lastTranscript: String = ""
    private var isDone: Bool = false
    private let maxSilenceSeconds: TimeInterval = 1.8
    private var silenceTimer: Timer?
    private let outputFile: String?

    init(outputFile: String? = nil) {
        self.outputFile = outputFile
        super.init()
    }

    func startListening(timeoutSeconds: TimeInterval) {
        SFSpeechRecognizer.requestAuthorization { authStatus in
            guard authStatus == .authorized else {
                FileHandle.standardError.write("Speech recognition not authorized: \(authStatus.rawValue)\n".data(using: .utf8)!)
                self.isDone = true
                return
            }
            self.recordAndRecognize(timeoutSeconds: timeoutSeconds)
        }

        let loopUntil = Date().addingTimeInterval(timeoutSeconds + 2.0)
        while !isDone && RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1)) {
            if Date() > loopUntil {
                break
            }
        }
    }

    private func recordAndRecognize(timeoutSeconds: TimeInterval) {
        recognitionRequest = SFSpeechAudioBufferRecognitionRequest()
        guard let recognitionRequest = recognitionRequest else {
            isDone = true
            return
        }

        recognitionRequest.shouldReportPartialResults = true

        let inputNode = audioEngine.inputNode
        let recordingFormat = inputNode.outputFormat(forBus: 0)
        inputNode.installTap(onBus: 0, bufferSize: 1024, format: recordingFormat) { buffer, _ in
            self.recognitionRequest?.append(buffer)
        }

        audioEngine.prepare()
        do {
            try audioEngine.start()
        } catch {
            FileHandle.standardError.write("Audio engine start error: \(error)\n".data(using: .utf8)!)
            isDone = true
            return
        }

        recognitionTask = speechRecognizer?.recognitionTask(with: recognitionRequest) { result, error in
            if let result = result {
                let text = result.bestTranscription.formattedString.trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty {
                    self.lastTranscript = text
                    self.resetSilenceTimer()
                }
                if result.isFinal {
                    self.finish()
                }
            }
            if error != nil {
                self.finish()
            }
        }

        Timer.scheduledTimer(withTimeInterval: timeoutSeconds, repeats: false) { _ in
            self.finish()
        }
    }

    private func resetSilenceTimer() {
        silenceTimer?.invalidate()
        silenceTimer = Timer.scheduledTimer(withTimeInterval: maxSilenceSeconds, repeats: false) { _ in
            self.finish()
        }
    }

    private func finish() {
        guard !isDone else { return }
        isDone = true
        silenceTimer?.invalidate()
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        recognitionTask?.cancel()

        if !lastTranscript.isEmpty {
            if let path = outputFile {
                try? lastTranscript.write(toFile: path, atomically: true, encoding: .utf8)
            }
            FileHandle.standardOutput.write("\(lastTranscript)\n".data(using: .utf8)!)
        }
    }
}

let args = CommandLine.arguments
var timeout: TimeInterval = 10.0
var outPath: String? = nil

if args.count > 1, let t = Double(args[1]) {
    timeout = t
}
if args.count > 2 {
    outPath = args[2]
}

let listener = AudioListener(outputFile: outPath)
listener.startListening(timeoutSeconds: timeout)
