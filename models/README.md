# Modelo facial opcional

O Furia Clips usa o detector **Blaze Face Short Range** do MediaPipe somente quando o facetracking é ativado e a composição do vídeo permite reenquadramento com segurança.

O arquivo `blaze_face_short_range.tflite` é obtido automaticamente pelo `run.bat` a partir do endpoint oficial do Google Storage. O launcher valida o SHA-256 antes de substituir qualquer arquivo local:

```text
URL: https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite
SHA-256: b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f
```

O binário fica fora do checkout Git para evitar duplicação e permitir reinstalação automática. Se não houver internet ou o MediaPipe não estiver disponível, o programa continua funcionando com a composição original, sem inventar um enquadramento facial.
