import SwiftUI

/// L6 Transparency UI — grounded 回答の透明性表示
///
/// AGENT_SKILL_BOUND_DESIGN.md §3.6 に対応。回答本文に加えて、
/// 出典タグ・信頼度・リスクバッジ・弁護士必須トリガー・未裏付け警告を
/// 「必ず可視化」する。ユーザーが AI の確信度を誤認しないための構造。
public struct HarnessAnswerView: View {
    public let answer: HarnessAnswer

    public init(answer: HarnessAnswer) {
        self.answer = answer
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                headerBadges
                if answer.refused {
                    refusalCard
                }
                answerBody
                if answer.hasUngrounded {
                    ungroundedCard
                }
                if !answer.sources.isEmpty {
                    sourcesSection
                }
                if answer.lawyerRequired {
                    lawyerCard
                }
                if let warn = answer.irreversibleActionWarning {
                    irreversibleCard(warn)
                }
                footer
            }
            .padding()
        }
    }

    // MARK: - ヘッダ（信頼度・リスク）

    private var headerBadges: some View {
        HStack(spacing: 12) {
            confidenceBadge
            riskBadge
            Spacer()
        }
    }

    private var confidenceBadge: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("信頼度").font(.caption2).foregroundColor(.secondary)
            HStack(spacing: 2) {
                ForEach(0..<5, id: \.self) { i in
                    Image(systemName: i < answer.confidenceBars ? "circle.fill" : "circle")
                        .font(.caption2)
                        .foregroundColor(confidenceColor)
                }
            }
        }
    }

    private var confidenceColor: Color {
        switch answer.confidenceBars {
        case 0...1: return .red
        case 2...3: return .orange
        default: return .green
        }
    }

    private var riskBadge: some View {
        let (label, color): (String, Color) = {
            switch answer.riskClass {
            case "irreversible": return ("不可逆", .red)
            case "high": return ("高リスク", .orange)
            case "med": return ("中リスク", .yellow)
            default: return ("低リスク", .green)
            }
        }()
        return VStack(alignment: .leading, spacing: 2) {
            Text("リスク").font(.caption2).foregroundColor(.secondary)
            Text(label)
                .font(.caption).bold()
                .padding(.horizontal, 8).padding(.vertical, 3)
                .background(color.opacity(0.18))
                .foregroundColor(color)
                .clipShape(Capsule())
        }
    }

    // MARK: - 本文

    private var answerBody: some View {
        Text(answer.answer)
            .font(.body)
            .textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - 各種カード

    private var refusalCard: some View {
        cardContainer(color: .gray, icon: "exclamationmark.triangle.fill") {
            Text("根拠が見つからず、確かな回答ができません。専門窓口・弁護士への相談を推奨します。")
                .font(.subheadline)
        }
    }

    private var ungroundedCard: some View {
        cardContainer(color: .orange, icon: "questionmark.circle.fill") {
            VStack(alignment: .leading, spacing: 4) {
                Text("未裏付けの主張（要確認）").font(.subheadline).bold()
                ForEach(Array(answer.verification.ungroundedClaims.enumerated()), id: \.offset) { _, c in
                    Text("• \(c.value)（\(c.type)）")
                        .font(.caption).foregroundColor(.secondary)
                }
            }
        }
    }

    private var lawyerCard: some View {
        cardContainer(color: .blue, icon: "person.fill.badge.plus") {
            Text("この件は弁護士への相談を推奨します。最終判断は専門家の確認のもとで行ってください。")
                .font(.subheadline)
        }
    }

    private func irreversibleCard(_ text: String) -> some View {
        cardContainer(color: .red, icon: "hand.raised.fill") {
            Text(text).font(.subheadline).bold()
        }
    }

    // MARK: - 出典

    private var sourcesSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("根拠（出典）").font(.headline)
            ForEach(answer.sources) { s in
                HStack(alignment: .top, spacing: 8) {
                    Text(s.id)
                        .font(.caption).bold().monospaced()
                        .padding(.horizontal, 6).padding(.vertical, 2)
                        .background(trustColor(s.trust).opacity(0.18))
                        .foregroundColor(trustColor(s.trust))
                        .clipShape(RoundedRectangle(cornerRadius: 4))
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(s.kindLabel)：\(s.citation)")
                            .font(.caption).bold()
                        Text(s.excerpt)
                            .font(.caption2).foregroundColor(.secondary)
                            .lineLimit(3)
                    }
                }
                .padding(.vertical, 4)
                Divider()
            }
        }
    }

    private func trustColor(_ trust: String) -> Color {
        switch trust {
        case "high": return .green
        case "medium": return .orange
        case "quarantined": return .red
        default: return .gray
        }
    }

    private var footer: some View {
        Text("本回答は参考であり、具体的な法律行動は弁護士へ相談してください。" +
             (answer.modelUsed.map { " (model: \($0))" } ?? ""))
            .font(.caption2)
            .foregroundColor(.secondary)
            .padding(.top, 8)
    }

    // MARK: - 共通カードコンテナ

    @ViewBuilder
    private func cardContainer<Content: View>(
        color: Color,
        icon: String,
        @ViewBuilder content: () -> Content
    ) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon).foregroundColor(color)
            content()
            Spacer(minLength: 0)
        }
        .padding(12)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(color.opacity(0.3), lineWidth: 1)
        )
    }
}
