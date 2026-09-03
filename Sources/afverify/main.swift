import AVFAudio
import zlib

let fileURL = URL(fileURLWithPath: ProcessInfo.processInfo.arguments[1])

var expectedCRC: UInt32 = 0
if !Scanner(string: ProcessInfo.processInfo.arguments[2]).scanHexInt32(&expectedCRC) {
    FileHandle.standardError.write("failed to parse as a UInt32 hex!\n".data(using: .utf8)!)
    exit(2)
}
let file = try AVAudioFile(forReading: fileURL, commonFormat: .pcmFormatInt16, interleaved: true)

let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat, frameCapacity: .init(file.length))!
try file.read(into: buffer)

let memory = buffer.int16ChannelData!.pointee

let res = zlib.crc32(0, .init(.init(memory)), buffer.frameLength * buffer.format.channelCount * .init(MemoryLayout<Int16>.size))

let ec: Int32 = res == expectedCRC ? 0 : 1
print(String(format: "calc=%08X,expected=%08X,exit=%d", res, expectedCRC, ec))
exit(ec)