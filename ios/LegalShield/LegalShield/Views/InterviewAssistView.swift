import SwiftUI

/// 防誘導取證畫面 — 保護「童言童語」的關鍵防線
///
/// 使用方式：
/// 1. 開啟 App，進入「防誘導訪談」模式
/// 2. 將手機放在桌上，麥克風朝向孩子
/// 3. App 即時監聽家長的提問
/// 4. 偵測到誘導問句時，螢幕閃爍紅燈並顯示建議替代問句
/// 5. 訪談結束後，自動生成「訪談品質報告」
struct InterviewAssistView: View {
    @StateObject private var copilot = InterviewCopilot()
    @State private var showReportSheet = false
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // 頂部狀態列
                InterviewStatusBar(copilot: copilot)
                
                // 主要內容區
                ScrollView {
                    VStack(spacing: 20) {
                        // 即時警告區
                        if let warning = copilot.currentWarning {
                            WarningBanner(warning: warning)
                                .transition(.move(edge: .top))
                        }
                        
                        // 逐字稿顯示
                        TranscriptView(transcript: copilot.transcript)
                        
                        // 訪談品質儀表
                        InterviewQualityDashboard(stats: copilot.sessionStats)
                    }
                    .padding()
                }
                
                // 底部控制列
                InterviewControlBar(copilot: copilot)
            }
            .navigationTitle("防誘導訪談")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { showReportSheet = true }) {
                        Image(systemName: "doc.text")
                    }
                    .disabled(copilot.transcript.isEmpty)
                }
            }
            .sheet(isPresented: $showReportSheet) {
                InterviewReportSheet(copilot: copilot)
            }
        }
    }
}

// MARK: - 狀態列

struct InterviewStatusBar: View {
    @ObservedObject var copilot: InterviewCopilot
    
    var body: some View {
        HStack {
            HStack(spacing: 6) {
                Image(systemName: copilot.isListening ? "waveform" : "waveform.slash")
                    .foregroundColor(copilot.isListening ? .red : .gray)
                    .font(.title3)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(copilot.isListening ? "監聽中..." : "等待啟動")
                        .font(.caption)
                        .fontWeight(.medium)
                    
                    if copilot.isListening {
                        Text("偵測誘導問句中")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            
            Spacer()
            
            // 風險計數器
            HStack(spacing: 4) {
                if copilot.sessionStats.criticalWarnings > 0 {
                    RiskBadge(count: copilot.sessionStats.criticalWarnings, color: .red)
                }
                if copilot.sessionStats.highWarnings > 0 {
                    RiskBadge(count: copilot.sessionStats.highWarnings, color: .orange)
                }
            }
        }
        .padding()
        .background(copilot.isListening ? Color.red.opacity(0.05) : Color(.systemGray6))
    }
}

struct RiskBadge: View {
    let count: Int
    let color: Color
    
    var body: some View {
        Text("\(count)")
            .font(.caption2)
            .fontWeight(.bold)
            .foregroundColor(.white)
            .frame(width: 20, height: 20)
            .background(color)
            .clipShape(Circle())
    }
}

// MARK: - 警告橫幅

struct WarningBanner: View {
    let warning: Warning
    @State private var animate = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: warning.pattern.severity.icon)
                    .font(.title2)
                    .foregroundColor(severityColor)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("偵測到：\(warning.pattern.name)")
                        .font(.headline)
                        .foregroundColor(severityColor)
                    
                    Text(warning.pattern.explanation)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                
                Spacer()
            }
            
            Divider()
            
            HStack {
                Image(systemName: "arrow.turn.up.right")
                    .foregroundColor(.green)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("建議替代問句：")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    
                    Text(warning.pattern.suggestion)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .foregroundColor(.green)
                }
            }
            .padding(.leading, 4)
        }
        .padding()
        .background(severityColor.opacity(0.1))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(severityColor.opacity(0.3), lineWidth: 2)
        )
        .cornerRadius(12)
        .scaleEffect(animate ? 1.0 : 0.95)
        .opacity(animate ? 1.0 : 0.8)
        .onAppear {
            withAnimation(.spring(response: 0.3)) {
                animate = true
            }
        }
    }
    
    private var severityColor: Color {
        switch warning.pattern.severity {
        case .critical: return .red
        case .high: return .orange
        case .medium: return .yellow
        case .low: return .blue
        }
    }
}

// MARK: - 逐字稿顯示

struct TranscriptView: View {
    let transcript: String
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("逐字稿")
                    .font(.headline)
                Spacer()
                Text("\(transcript.count) 字")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            
            if transcript.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "mic.slash.fill")
                        .font(.system(size: 32))
                        .foregroundStyle(.tertiary)
                    Text("點擊下方按鈕開始錄音")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, minHeight: 150)
                .background(Color(.systemGray6))
                .cornerRadius(12)
            } else {
                Text(transcript)
                    .font(.body)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
            }
        }
    }
}

// MARK: - 訪談品質儀表

struct InterviewQualityDashboard: View {
    let stats: SessionStats
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("訪談品質儀表")
                .font(.headline)
            
            HStack(spacing: 12) {
                QualityMetricCard(
                    icon: "clock.fill",
                    value: formatDuration(stats.duration),
                    label: "訪談時長"
                )
                
                QualityMetricCard(
                    icon: "exclamationmark.triangle.fill",
                    value: "\(stats.leadingQuestionCount)",
                    label: "誘導問句",
                    color: stats.leadingQuestionCount > 0 ? .orange : .green
                )
            }
            
            // 品質評分條
            QualityBar(
                critical: stats.criticalWarnings,
                high: stats.highWarnings,
                medium: stats.mediumWarnings
            )
        }
    }
    
    private func formatDuration(_ duration: TimeInterval) -> String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        if minutes > 0 {
            return "\(minutes)分\(seconds)秒"
        }
        return "\(seconds)秒"
    }
}

struct QualityMetricCard: View {
    let icon: String
    let value: String
    let label: String
    var color: Color = .blue
    
    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.title3)
                .foregroundColor(color)
            Text(value)
                .font(.title3)
                .fontWeight(.bold)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }
}

struct QualityBar: View {
    let critical: Int
    let high: Int
    let medium: Int
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 4) {
                if critical > 0 {
                    Color.red
                        .frame(height: 8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                if high > 0 {
                    Color.orange
                        .frame(height: 8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                if medium > 0 {
                    Color.yellow
                        .frame(height: 8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                if critical == 0 && high == 0 && medium == 0 {
                    Color.green
                        .frame(height: 8)
                        .frame(maxWidth: .infinity)
                }
            }
            .clipShape(Capsule())
            
            HStack {
                if critical > 0 {
                    Label("危急 \(critical)", systemImage: "exclamationmark.octagon.fill")
                        .font(.caption2)
                        .foregroundColor(.red)
                }
                if high > 0 {
                    Label("高風險 \(high)", systemImage: "exclamationmark.triangle.fill")
                        .font(.caption2)
                        .foregroundColor(.orange)
                }
                if medium > 0 {
                    Label("中風險 \(medium)", systemImage: "exclamationmark.circle.fill")
                        .font(.caption2)
                        .foregroundColor(.yellow)
                }
                if critical == 0 && high == 0 && medium == 0 {
                    Label("品質優良", systemImage: "checkmark.shield.fill")
                        .font(.caption2)
                        .foregroundColor(.green)
                }
            }
        }
    }
}

// MARK: - 控制列

struct InterviewControlBar: View {
    @ObservedObject var copilot: InterviewCopilot
    @State private var showStopConfirm = false
    
    var body: some View {
        VStack(spacing: 0) {
            Divider()
            
            HStack(spacing: 20) {
                if copilot.isListening {
                    // 停止按鈕
                    Button(action: { showStopConfirm = true }) {
                        HStack {
                            Image(systemName: "stop.circle.fill")
                            Text("結束訪談")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.red)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                    .alert("確認結束？", isPresented: $showStopConfirm) {
                        Button("取消", role: .cancel) {}
                        Button("結束訪談", role: .destructive) {
                            copilot.stopListening()
                        }
                    } message: {
                        Text("結束後將生成訪談品質報告。")
                    }
                } else {
                    // 開始按鈕
                    Button(action: {
                        try? copilot.startListening()
                    }) {
                        HStack {
                            Image(systemName: "mic.circle.fill")
                            Text("開始防誘導訪談")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(.green)
                        .foregroundColor(.white)
                        .cornerRadius(12)
                    }
                }
            }
            .padding()
        }
        .background(.ultraThinMaterial)
    }
}

// MARK: - 報告 Sheet

struct InterviewReportSheet: View {
    @ObservedObject var copilot: InterviewCopilot
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // 品質評估標題
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("訪談品質報告")
                                .font(.title2)
                                .fontWeight(.bold)
                            
                            Text("產生時間：\(Date().iso8601)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        
                        Spacer()
                        
                        QualityGradeBadge(stats: copilot.sessionStats)
                    }
                    
                    Divider()
                    
                    // 統計數據
                    InterviewStatsGrid(stats: copilot.sessionStats)
                    
                    // 警告歷史
                    if !copilot.warningHistory.isEmpty {
                        WarningHistoryList(warnings: copilot.warningHistory)
                    }
                    
                    // 完整逐字稿
                    VStack(alignment: .leading, spacing: 8) {
                        Text("完整逐字稿")
                            .font(.headline)
                        
                        Text(copilot.transcript)
                            .font(.body)
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(.systemGray6))
                            .cornerRadius(12)
                    }
                    
                    // 專業建議
                    VStack(alignment: .leading, spacing: 8) {
                        Text("專業建議")
                            .font(.headline)
                        
                        Text(copilot.sessionStats.assessment)
                            .font(.body)
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.green.opacity(0.1))
                            .cornerRadius(12)
                    }
                }
                .padding()
            }
            .navigationTitle("訪談報告")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }
                }
                
                ToolbarItem(placement: .topBarLeading) {
                    ShareLink(
                        item: copilot.generateSessionReport(),
                        subject: Text("LegalShield 訪談報告"),
                        message: Text("附件為本次訪談品質報告。")
                    ) {
                        Image(systemName: "square.and.arrow.up")
                    }
                }
            }
        }
    }
}

struct QualityGradeBadge: View {
    let stats: SessionStats
    
    var body: some View {
        let grade = computeGrade()
        Text(grade)
            .font(.system(size: 36, weight: .bold))
            .foregroundColor(gradeColor(grade))
            .frame(width: 60, height: 60)
            .background(gradeColor(grade).opacity(0.1))
            .clipShape(Circle())
    }
    
    private func computeGrade() -> String {
        if stats.criticalWarnings > 0 { return "F" }
        if stats.highWarnings > 3 { return "D" }
        if stats.highWarnings > 1 { return "C" }
        if stats.mediumWarnings > 2 { return "B" }
        return "A"
    }
    
    private func gradeColor(_ grade: String) -> Color {
        switch grade {
        case "A": return .green
        case "B": return .blue
        case "C": return .yellow
        case "D": return .orange
        case "F": return .red
        default: return .gray
        }
    }
}

struct InterviewStatsGrid: View {
    let stats: SessionStats
    
    var body: some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            StatBox(value: formatDuration(stats.duration), label: "訪談時長")
            StatBox(value: "\(stats.totalWords)", label: "總字數")
            StatBox(value: "\(stats.leadingQuestionCount)", label: "誘導問句", isNegative: stats.leadingQuestionCount > 0)
            StatBox(value: "\(stats.criticalWarnings + stats.highWarnings + stats.mediumWarnings)", label: "風險次數", isNegative: true)
        }
    }
    
    private func formatDuration(_ duration: TimeInterval) -> String {
        let minutes = Int(duration) / 60
        let seconds = Int(duration) % 60
        return "\(minutes)分\(seconds)秒"
    }
}

struct StatBox: View {
    let value: String
    let label: String
    var isNegative: Bool = false
    
    var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.title3)
                .fontWeight(.bold)
                .foregroundColor(isNegative ? .red : .primary)
            Text(label)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}

struct WarningHistoryList: View {
    let warnings: [Warning]
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("偵測到的誘導問句 (\(warnings.count))")
                .font(.headline)
            
            ForEach(warnings) { warning in
                HStack(spacing: 8) {
                    Image(systemName: warning.pattern.severity.icon)
                        .foregroundColor(severityColor(warning.pattern.severity))
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text(warning.pattern.name)
                            .font(.subheadline)
                            .fontWeight(.medium)
                        Text(warning.detectedText)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    
                    Spacer()
                }
                .padding(.vertical, 4)
            }
        }
    }
    
    private func severityColor(_ severity: WarningSeverity) -> Color {
        switch severity {
        case .critical: return .red
        case .high: return .orange
        case .medium: return .yellow
        case .low: return .blue
        }
    }
}
