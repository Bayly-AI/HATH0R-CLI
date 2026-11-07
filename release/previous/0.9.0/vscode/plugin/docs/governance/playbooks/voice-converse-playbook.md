# Playbook: Voice Conversational Interface (`voice-converse-factory`)

## Operator Playbook

### 1. Starting a Conversational Meeting Session
To launch a continuous two-way meeting session with the agent:
```bash
hath0r voice converse
```
Or with specific meeting duration and target repository context:
```bash
hath0r voice converse --repo /path/to/project --max-turns 10
```

### 2. Standup & Meeting Participation Mode
To activate hands-free meeting mode where the agent listens and speaks when addressed or when reporting standup status:
```bash
hath0r voice meeting --mode standup
```

### 3. Proactive Verbal Announcement
To make the agent verbally speak an update upon task completion:
```bash
hath0r voice speak "The test suite has completed successfully with zero failures."
```

### 4. Running via Factory Workflow
```bash
hath0r workflow run voice-converse-factory converse-session
```
