Starting video analysis...
Submitting video analysis task...
Error: failed to submit analysis task: SubmitVideoAnalysis RPC failed: deadline_exceeded: Post "[internal endpoint]": net/http: request canceled while waiting for connection (Client.Timeout exceeded while awaiting headers)
Usage:
  manus-analyze-video <video_url_or_path> <prompt> [flags]

Examples:
  manus-analyze-video "https://www.youtube.com/watch?v=xxx" "summarize the key points"
  manus-analyze-video "/path/to/video.mp4" "describe what happens in this video"

Flags:
  -h, --help      help for manus-analyze-video
  -v, --version   version for manus-analyze-video
