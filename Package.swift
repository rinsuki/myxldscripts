// swift-tools-version: 6.3

import PackageDescription

let package = Package(
    name: "myxldscripts",
    products: [
        .executable(name: "afverify", targets: ["afverify"])
    ],
    targets: [
        .executableTarget(
            name: "afverify"
        ),
    ],
    swiftLanguageModes: [.v6]
)
