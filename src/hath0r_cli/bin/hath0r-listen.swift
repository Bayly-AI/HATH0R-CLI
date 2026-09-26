import AVFoundation
import Foundation

class VoiceAudioRecorder: NSObject, AVAudioRecorderDelegate {
    private var recorder: AVAudioRecorder?
    private let outputFile: URL
    private let maxDuration: TimeInterval
    private var isDone: Bool = false
    private var silenceTimer: Timer?
    private var speechDetected: Bool = false
    private let silenceThresholdDB: Float = -42.0
    private let pauseSilenceSeconds: TimeInterval = 1.4

    init(outputFile: URL, maxDuration: TimeInterval = 8.0) {
        self.outputFile = outputFile
        self.maxDuration = maxDuration
        super.init()
    }

    func record() {
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16000.0,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue,
        ]

        do {
            recorder = try AVAudioRecorder(url: outputFile, settings: settings)
            recorder?.delegate = self
            recorder?.isMeteringEnabled = true
            recorder?.record(forDuration: maxDuration)
        } catch {
            FileHandle.standardError.write("Audio recorder init error: \(error)\n".data(using: .utf8)!)
            return
        }

        // Metering poll loop
        let pollTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] timer in
            guard let self = self, let recorder = self.recorder, recorder.isRecording else {
                timer.invalidate()
                return
            }
            recorder.updateMeters()
            let power = recorder.averagePower(forChannel: 0)

            if power > self.silenceThresholdDB {
                self.speechDetected = true
                self.silenceTimer?.invalidate()
                self.silenceTimer = Timer.scheduledTimer(withTimeInterval: self.pauseSilenceSeconds, repeats: false) { [weak self] _ in
                    self?.finish()
                }
            }
        }

        let loopUntil = Date().addingTimeInterval(maxDuration + 1.0)
        while !isDone && RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1)) {
            if Date() > loopUntil {
                break
            }
        }

        pollTimer.invalidate()
        finish()
    }

    private func finish() {
        guard !isDone else { return }
        isDone = true
        silenceTimer?.invalidate()
        if let rec = recorder, rec.isRecording {
            rec.stop()
        }
        FileHandle.standardOutput.write("RECORD_COMPLETE:\(outputFile.path)\n".data(using: .utf8)!)
    }
}

let args = CommandLine.arguments
var duration: TimeInterval = 7.0
var outPath = "/tmp/hath0r_voice_input.m4a"

if args.count > 1, let d = Double(args[1]) {
    duration = d
}
if args.count > 2 {
    outPath = args[2]
}

let fileURL = URL(fileURLWithPath: outPath)
try? FileManager.default.removeItem(at: fileURL)

let voiceRecorder = VoiceAudioRecorder(outputFile: fileURL, maxDuration: duration)
voiceRecorder.record()
