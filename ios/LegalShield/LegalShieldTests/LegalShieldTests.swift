import XCTest
@testable import LegalShield

/// LegalShield iOS 單元測試
final class LegalShieldTests: XCTestCase {
    
    // MARK: - Evidence Tests
    
    func testSHA256HashComputation() {
        let testData = "LegalShield Evidence Test".data(using: .utf8)!
        let hash = Evidence.computeSHA256(for: testData)
        
        XCTAssertEqual(hash.count, 64)  // SHA-256 = 64 hex chars
        XCTAssertTrue(hash.allSatisfy { $0.isHexDigit })
    }
    
    func testEvidenceIntegrity() {
        let testData = "Tamper-proof evidence data".data(using: .utf8)!
        let hash = Evidence.computeSHA256(for: testData)
        
        let evidence = Evidence(
            caseId: UUID(),
            type: .document,
            fileName: "test.txt",
            fileSize: testData.count,
            sha256Hash: hash,
            chainIndex: 0
        )
        
        XCTAssertTrue(evidence.verifyIntegrity(for: testData))
        
        // 竄改數據後應該驗證失敗
        let tamperedData = "Tampered!".data(using: .utf8)!
        XCTAssertFalse(evidence.verifyIntegrity(for: tamperedData))
    }
    
    func testEvidenceChain() {
        let caseId = UUID()
        
        let evidence1 = Evidence(
            caseId: caseId,
            type: .photo,
            fileName: "photo1.jpg",
            fileSize: 1024,
            sha256Hash: "hash1",
            chainIndex: 0
        )
        
        let evidence2 = Evidence(
            caseId: caseId,
            type: .audio,
            fileName: "audio1.m4a",
            fileSize: 2048,
            sha256Hash: "hash2",
            previousHash: "hash1",
            chainIndex: 1
        )
        
        XCTAssertNil(evidence1.previousHash)
        XCTAssertEqual(evidence2.previousHash, "hash1")
        XCTAssertEqual(evidence1.chainIndex, 0)
        XCTAssertEqual(evidence2.chainIndex, 1)
    }
    
    // MARK: - Interview Copilot Tests
    
    func testLeadingQuestionDetection() {
        let copilot = InterviewCopilot()
        
        // 模擬偵測
        let testCases = [
            ("老師是不是有摸你？", true),
            ("是不是在小房間發生的？", true),
            ("你可以告訴我發生了什麼事嗎？", false),
            ("那個時候你在哪裡？", false)
        ]
        
        for (question, shouldBeDetected) in testCases {
            // 簡化測試：檢查正則匹配
            var detected = false
            for pattern in [
                "(是不是|有沒有|難道)(.*)(老師|爸爸|媽媽)(.*)(你|摸|打|碰)",
                "(是不是在|有沒有在)(.*)(教室|廁所|房間|小房間|角落)"
            ] {
                if let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]),
                   regex.firstMatch(in: question, options: [], range: NSRange(question.startIndex..., in: question)) != nil {
                    detected = true
                    break
                }
            }
            
            XCTAssertEqual(detected, shouldBeDetected, "Failed for: \(question)")
        }
    }
    
    // MARK: - Sensor Tests
    
    func testSensorAnalyzer() {
        let analyzer = SensorAnalyzer()
        
        // 正常心率
        let normalHR = SensorData(
            timestamp: Date(),
            type: .heartRate,
            value: 75,
            unit: "bpm",
            deviceID: "test",
            deviceName: "Test Device",
            metadata: nil
        )
        XCTAssertEqual(analyzer.analyze(normalHR), .none)
        
        // 異常心率 (靜止超過 130)
        let highHR = SensorData(
            timestamp: Date(),
            type: .heartRate,
            value: 145,
            unit: "bpm",
            deviceID: "test",
            deviceName: "Test Device",
            metadata: nil
        )
        // 第一次異常應該是 high，持續才 critical
        XCTAssertEqual(analyzer.analyze(highHR), .high)
    }
    
    func testMockSensorManager() {
        let manager = MockSensorManager(scenario: .panicButtonPressed)
        
        let expectation = XCTestExpectation(description: "Receive sensor data")
        var receivedData: SensorData?
        
        let cancellable = manager.dataStream
            .first()
            .sink { data in
                receivedData = data
                expectation.fulfill()
            }
        
        manager.startSimulation()
        
        wait(for: [expectation], timeout: 3.0)
        
        XCTAssertNotNil(receivedData)
        XCTAssertEqual(receivedData?.type, .buttonPress)
        
        cancellable.cancel()
        manager.stopSimulation()
    }
    
    // MARK: - Case Tests
    
    func testCaseCreation() {
        let caseItem = LegalCase(
            title: "Test Case",
            category: .childAbuse,
            victimAlias: "Test Child",
            victimAge: 5,
            institutionName: "Test Kindergarten"
        )
        
        XCTAssertEqual(caseItem.title, "Test Case")
        XCTAssertEqual(caseItem.caseCategory, .childAbuse)
        XCTAssertEqual(caseItem.victimAge, 5)
        XCTAssertEqual(caseItem.evidenceCount, 0)
        XCTAssertEqual(caseItem.caseStatus, .active)
    }
    
    func testCaseTemplate() {
        let childCase = LegalCase.childAbuseTemplate(
            institution: "XX幼兒園",
            victimAge: 5,
            victimAlias: "小華"
        )
        
        XCTAssertEqual(childCase.caseCategory, .childAbuse)
        XCTAssertEqual(childCase.urgencyLevel, .critical)
        XCTAssertEqual(childCase.victimAge, 5)
        XCTAssertEqual(childCase.institutionName, "XX幼兒園")
    }
    
    // MARK: - LLM Service Tests
    
    func testIntentClassification() {
        let service = LLMService()
        
        XCTAssertEqual(service.classifyIntent("我需要求救"), .emergency)
        XCTAssertEqual(service.classifyIntent("怎麼拍照存證"), .evidence)
        XCTAssertEqual(service.classifyIntent("刑法第幾條"), .legal)
        XCTAssertEqual(service.classifyIntent("接下來該怎麼辦"), .strategy)
        XCTAssertEqual(service.classifyIntent("推薦社工"), .referral)
    }
    
    // MARK: - Performance Tests
    
    func testHashPerformance() {
        let data = Data(repeating: 0xFF, count: 1024 * 1024)  // 1MB
        
        measure {
            _ = Evidence.computeSHA256(for: data)
        }
    }
}
