import Foundation
import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    print("[]")
    exit(0)
}

let imagePath = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: imagePath),
      let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("[]")
    exit(0)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hant", "zh-Hans", "en-US"]
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
try? handler.perform([request])

var results: [[String: Any]] = []
let imgWidth = Double(cgImage.width)
let imgHeight = Double(cgImage.height)

if let observations = request.results {
    for obs in observations {
        let topCandidate = obs.topCandidates(1).first?.string ?? ""
        let bbox = obs.boundingBox
        let x = bbox.origin.x * imgWidth
        let y = (1.0 - bbox.origin.y - bbox.size.height) * imgHeight
        let w = bbox.size.width * imgWidth
        let h = bbox.size.height * imgHeight
        let cx = x + w / 2.0
        let cy = y + h / 2.0

        results.append([
            "text": topCandidate,
            "bbox": [Int(x), Int(y), Int(x + w), Int(y + h)],
            "center": [Int(cx), Int(cy)],
            "confidence": obs.confidence
        ])
    }
}

if let jsonData = try? JSONSerialization.data(withJSONObject: results, options: []),
   let jsonString = String(data: jsonData, encoding: .utf8) {
    print(jsonString)
}
