"""Dark immersive landing page for the Streamlit app home screen."""

from __future__ import annotations

from html import escape

import streamlit as st


TEXT = {
    "zh": {
        "eyebrow": "资产管理智能分析",
        "title": "文旅消费基础设施 REITs 智能评估平台",
        "subtitle": "面向景区、酒店与度假综合体的资产适配性评分、风险预警、情景压力测试与数据质量评估工具。",
        "primary_cta": "进入评分模型",
        "secondary_cta": "查看数据质量",
        "kpis": [
            ("资产样本", "{asset_count}"),
            ("评分模块", "5"),
            ("数据源", "{source_count}"),
            ("自动报告", "支持"),
        ],
        "core_title": "核心能力",
        "features": [
            ("01", "监管准入检查", "资产权属、经营历史、现金流和分派能力的准入筛查。"),
            ("02", "REITs 适配性评分", "基于现金流、文旅运营、服务质量、风险韧性和数据成熟度的 100 分评分。"),
            ("03", "公开财务数据管道", "接入 AKShare 公开财务数据，支持 Demo / Verified 数据源切换。"),
            ("04", "字段来源标注", "区分已核验公开数据、模型派生指标和估算 / 示例数据。"),
            ("05", "情景压力测试", "模拟收入下降、客流下降、成本上升等压力情景。"),
            ("06", "自动报告生成", "根据当前资产、数据源和评分结果生成 Markdown 报告。"),
        ],
        "workflow_title": "评估流程",
        "workflow": [
            ("01", "Gatekeeper", "准入条件筛查"),
            ("02", "Fit Score", "适配性评分"),
            ("03", "Risk Warning", "风险预警"),
            ("04", "Scenario Test", "情景压力测试"),
            ("05", "Report", "报告生成"),
        ],
        "trust_title": "数据可信度与透明度",
        "trust_body": "平台不会将公开披露数据、模型派生指标与估算字段混为一谈，而是通过字段来源标注和 Data Quality 模块披露数据边界。",
        "trust_items": [
            ("已核验公开数据", "收入、经营现金流、总资产、总负债、资产负债率"),
            ("模型派生指标", "OCF Margin、Debt Ratio、Revenue Stability、OCF Stability"),
            ("估算 / 示例 / 代理数据", "NOI、AFFO、维护性资本开支、运营和风险代理指标"),
        ],
        "footer": "本平台为作品集演示和资产管理分析支持工具，不构成投资建议、官方评级、估值意见或监管结论。",
    },
    "en": {
        "eyebrow": "Asset Management Intelligence",
        "title": "Tourism REIT Intelligence Platform",
        "subtitle": "An intelligence platform for evaluating tourism consumption infrastructure assets, combining REIT suitability scoring, risk warning, scenario stress testing, and data quality assessment.",
        "primary_cta": "Open Fit Score",
        "secondary_cta": "View Data Quality",
        "kpis": [
            ("Asset sample", "{asset_count}"),
            ("Scoring modules", "5"),
            ("Data sources", "{source_count}"),
            ("Auto reports", "Supported"),
        ],
        "core_title": "Core Capabilities",
        "features": [
            ("01", "Regulatory Gatekeeper", "Pre-screen ownership, operating history, cash flow, and distribution capacity."),
            ("02", "REITs Suitability Score", "A 100-point score across cash flow, tourism operations, service quality, risk resilience, and data maturity."),
            ("03", "Public Financial Data Pipeline", "Connects AKShare public financial data and supports Demo / Verified source switching."),
            ("04", "Field Source Labels", "Distinguishes verified public data, model-derived indicators, and estimated/demo data."),
            ("05", "Scenario Stress Testing", "Simulates revenue decline, visitor-volume decline, cost increases, and other downside cases."),
            ("06", "Automatic Report Generation", "Generates Markdown reports from the current asset, data source, and scoring outputs."),
        ],
        "workflow_title": "Evaluation Workflow",
        "workflow": [
            ("01", "Gatekeeper", "Eligibility screen"),
            ("02", "Fit Score", "Suitability scoring"),
            ("03", "Risk Warning", "Risk signals"),
            ("04", "Scenario Test", "Stress testing"),
            ("05", "Report", "Report generation"),
        ],
        "trust_title": "Data Trust and Transparency",
        "trust_body": "The platform separates public disclosure data, model-derived indicators, and estimated fields through field source labels and the Data Quality module.",
        "trust_items": [
            ("Verified public data", "Revenue, operating cash flow, total assets, total debt, debt ratio"),
            ("Model-derived indicators", "OCF Margin, Debt Ratio, Revenue Stability, OCF Stability"),
            ("Estimated, demo, or proxy data", "NOI, AFFO, maintenance CAPEX, operation and risk proxy fields"),
        ],
        "footer": "This platform is a portfolio demonstration and asset-management analytics support tool. It is not investment advice, an official rating, a valuation opinion, or a regulatory conclusion.",
    },
}


def _text(language: str) -> dict:
    return TEXT["zh"] if language == "zh" else TEXT["en"]


def render_html(html: str) -> None:
    """Render trusted landing-page HTML in one place."""
    st.markdown(html, unsafe_allow_html=True)


def render_landing_styles() -> None:
    render_html(
        """
<style>
:root {
  --bg: #050B16;
  --panel: rgba(15, 23, 42, 0.72);
  --panel-strong: rgba(15, 23, 42, 0.92);
  --text: #F8FAFC;
  --muted: #94A3B8;
  --line: rgba(148, 163, 184, 0.22);
  --blue: #38BDF8;
  --violet: #8B5CF6;
  --green: #22C55E;
  --amber: #F59E0B;
}
.stApp {
  background:
    radial-gradient(circle at 24% 8%, rgba(56, 189, 248, 0.20), transparent 28rem),
    radial-gradient(circle at 84% 16%, rgba(139, 92, 246, 0.24), transparent 30rem),
    linear-gradient(180deg, #050B16 0%, #08111F 46%, #050B16 100%);
  color: var(--text);
}
[data-testid="stHeader"] { background: rgba(5, 11, 22, 0); }
[data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 1200px;
  padding-top: 1.4rem;
  padding-bottom: 3rem;
}
.landing-shell {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 28px;
  min-height: 560px;
  padding: 74px 58px 46px;
  background:
    linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.64)),
    radial-gradient(circle at 70% 40%, rgba(56, 189, 248, 0.16), transparent 22rem);
  box-shadow: 0 26px 90px rgba(0, 0, 0, 0.38);
}
.landing-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: linear-gradient(90deg, transparent 0%, #000 14%, #000 82%, transparent 100%);
}
.landing-shell::after {
  content: "";
  position: absolute;
  width: 760px;
  height: 760px;
  right: -260px;
  top: -170px;
  border-radius: 999px;
  background:
    radial-gradient(circle, rgba(56, 189, 248, 0.18), transparent 54%),
    conic-gradient(from 220deg, rgba(56, 189, 248, 0.0), rgba(56, 189, 248, 0.28), rgba(139, 92, 246, 0.22), rgba(34, 197, 94, 0.12), rgba(56, 189, 248, 0.0));
  filter: blur(0.2px);
}
.hero-content {
  position: relative;
  z-index: 2;
  max-width: 820px;
}
.eyebrow {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  padding: 8px 13px;
  border: 1px solid rgba(56, 189, 248, 0.34);
  border-radius: 999px;
  color: #BAE6FD;
  background: rgba(14, 165, 233, 0.11);
  font-size: 13px;
  letter-spacing: 0;
}
.eyebrow-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--green);
  box-shadow: 0 0 18px rgba(34, 197, 94, 0.76);
}
.hero-title {
  margin: 28px 0 18px;
  max-width: 880px;
  color: var(--text);
  font-size: clamp(42px, 6vw, 78px);
  line-height: 1.04;
  font-weight: 780;
  letter-spacing: 0;
}
.hero-subtitle {
  max-width: 760px;
  color: #CBD5E1;
  font-size: 18px;
  line-height: 1.8;
}
.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 28px;
}
.pill {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  padding: 9px 13px;
  color: #E2E8F0;
  background: rgba(15, 23, 42, 0.52);
  backdrop-filter: blur(14px);
  font-size: 13px;
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 34px;
}
.hero-action {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 0 18px;
  border-radius: 12px;
  text-decoration: none !important;
  font-weight: 680;
  letter-spacing: 0;
}
.hero-action.primary {
  color: #04111F !important;
  background: linear-gradient(135deg, var(--blue), #A78BFA);
  box-shadow: 0 14px 34px rgba(56, 189, 248, 0.26);
}
.hero-action.secondary {
  color: #E2E8F0 !important;
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(15, 23, 42, 0.64);
}
.hero-visual {
  position: absolute;
  right: 44px;
  bottom: 42px;
  z-index: 1;
  width: min(410px, 38vw);
  min-width: 280px;
}
.signal-panel {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  padding: 16px;
  background: rgba(2, 6, 23, 0.42);
  backdrop-filter: blur(18px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 20px 70px rgba(0,0,0,0.28);
}
.signal-row {
  display: grid;
  grid-template-columns: 74px 1fr 42px;
  gap: 12px;
  align-items: center;
  margin: 12px 0;
  color: #CBD5E1;
  font-size: 12px;
}
.signal-bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
  overflow: hidden;
}
.signal-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--blue), var(--violet));
}
.stat-grid, .bento-grid, .trust-grid {
  display: grid;
  gap: 16px;
}
.stat-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: -42px 24px 72px;
  position: relative;
  z-index: 4;
}
.stat-card, .bento-card, .workflow-step, .trust-card {
  border: 1px solid var(--line);
  background: var(--panel);
  backdrop-filter: blur(18px);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
.stat-card {
  border-radius: 18px;
  padding: 22px;
}
.stat-value {
  color: var(--text);
  font-size: 32px;
  line-height: 1.1;
  font-weight: 760;
}
.stat-label {
  margin-top: 8px;
  color: var(--muted);
  font-size: 13px;
}
.section {
  margin: 72px 0;
}
.section-title {
  color: var(--text);
  font-size: 30px;
  font-weight: 760;
  letter-spacing: 0;
  margin: 0 0 22px;
}
.bento-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.bento-card {
  min-height: 188px;
  border-radius: 20px;
  padding: 22px;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}
.bento-card:hover {
  transform: translateY(-3px);
  border-color: rgba(56, 189, 248, 0.42);
  background: rgba(15, 23, 42, 0.84);
}
.card-number {
  color: var(--blue);
  font-size: 13px;
  font-weight: 760;
}
.card-title {
  margin-top: 18px;
  color: var(--text);
  font-size: 18px;
  font-weight: 720;
}
.card-text {
  margin-top: 10px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.7;
}
.workflow-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}
.workflow-step {
  border-radius: 18px;
  min-height: 132px;
  padding: 18px;
  position: relative;
}
.workflow-step::after {
  content: "";
  position: absolute;
  top: 50%;
  right: -14px;
  width: 14px;
  height: 1px;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0.5), transparent);
}
.workflow-step:last-child::after { display: none; }
.workflow-index {
  color: var(--amber);
  font-size: 12px;
  font-weight: 760;
}
.workflow-name {
  margin-top: 16px;
  color: var(--text);
  font-size: 16px;
  font-weight: 720;
}
.workflow-desc {
  margin-top: 8px;
  color: var(--muted);
  font-size: 13px;
}
.trust-panel {
  border: 1px solid rgba(56, 189, 248, 0.24);
  border-radius: 24px;
  padding: 28px;
  background:
    radial-gradient(circle at 18% 20%, rgba(34, 197, 94, 0.10), transparent 18rem),
    rgba(15, 23, 42, 0.72);
}
.trust-body {
  max-width: 860px;
  color: #CBD5E1;
  font-size: 16px;
  line-height: 1.8;
}
.trust-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 22px;
}
.trust-card {
  border-radius: 18px;
  padding: 18px;
}
.trust-label {
  color: var(--text);
  font-weight: 720;
}
.trust-fields {
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}
.landing-footer {
  border-top: 1px solid var(--line);
  margin-top: 72px;
  padding: 24px 0 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.7;
}
@media (max-width: 960px) {
  .landing-shell { padding: 46px 26px; min-height: 640px; }
  .hero-visual { position: relative; right: auto; bottom: auto; width: 100%; margin-top: 36px; }
  .stat-grid, .bento-grid, .trust-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .workflow-row { grid-template-columns: 1fr; }
  .workflow-step::after { display: none; }
}
@media (max-width: 640px) {
  [data-testid="stAppViewContainer"] > .main .block-container { padding-left: 1rem; padding-right: 1rem; }
  .landing-shell { border-radius: 20px; padding: 34px 20px; }
  .hero-title { font-size: 40px; }
  .hero-subtitle { font-size: 16px; }
  .stat-grid, .bento-grid, .trust-grid { grid-template-columns: 1fr; margin-left: 0; margin-right: 0; }
}
</style>
        """
    )


def render_hero_section(language: str) -> None:
    text = _text(language)
    render_html(
        f"""
<section class="landing-shell">
  <div class="hero-content">
    <div class="eyebrow"><span class="eyebrow-dot"></span>{escape(text["eyebrow"])}</div>
    <h1 class="hero-title">{escape(text["title"])}</h1>
    <p class="hero-subtitle">{escape(text["subtitle"])}</p>
    <div class="hero-pills">
      <span class="pill">Verified Data Pipeline</span>
      <span class="pill">Model Explainability</span>
      <span class="pill">Scenario Stress Testing</span>
    </div>
    <div class="hero-actions">
      <a class="hero-action primary" href="/REIT_Fit_Score" target="_self">{escape(text["primary_cta"])}</a>
      <a class="hero-action secondary" href="/Data_Quality" target="_self">{escape(text["secondary_cta"])}</a>
    </div>
  </div>
  <div class="hero-visual">
    <div class="signal-panel">
      <div class="signal-row"><span>Cash Flow</span><span class="signal-bar"><span class="signal-fill" style="width: 76%"></span></span><span>76</span></div>
      <div class="signal-row"><span>Risk</span><span class="signal-bar"><span class="signal-fill" style="width: 48%"></span></span><span>48</span></div>
      <div class="signal-row"><span>Quality</span><span class="signal-bar"><span class="signal-fill" style="width: 88%"></span></span><span>88</span></div>
      <div class="signal-row"><span>Data</span><span class="signal-bar"><span class="signal-fill" style="width: 64%"></span></span><span>64</span></div>
    </div>
  </div>
</section>
        """
    )


def render_floating_stats(language: str, asset_count: int, source_count: int) -> None:
    cards = []
    for label, value_template in _text(language)["kpis"]:
        value = value_template.format(asset_count=asset_count, source_count=source_count)
        cards.append(
            f"""
<div class="stat-card">
  <div class="stat-value">{escape(value)}</div>
  <div class="stat-label">{escape(label)}</div>
</div>
            """
        )
    render_html(f"<section class=\"stat-grid\">{''.join(cards)}</section>")


def render_bento_grid(language: str) -> None:
    cards = []
    for number, title, body in _text(language)["features"]:
        cards.append(
            f"""
<article class="bento-card">
  <div class="card-number">{escape(number)}</div>
  <div class="card-title">{escape(title)}</div>
  <div class="card-text">{escape(body)}</div>
</article>
            """
        )
    render_html(
        f"""
<section class="section">
  <h2 class="section-title">{escape(_text(language)["core_title"])}</h2>
  <div class="bento-grid">{''.join(cards)}</div>
</section>
        """
    )


def render_workflow_section(language: str) -> None:
    steps = []
    for number, name, desc in _text(language)["workflow"]:
        steps.append(
            f"""
<div class="workflow-step">
  <div class="workflow-index">{escape(number)}</div>
  <div class="workflow-name">{escape(name)}</div>
  <div class="workflow-desc">{escape(desc)}</div>
</div>
            """
        )
    render_html(
        f"""
<section class="section">
  <h2 class="section-title">{escape(_text(language)["workflow_title"])}</h2>
  <div class="workflow-row">{''.join(steps)}</div>
</section>
        """
    )


def render_data_trust_section(language: str) -> None:
    trust_cards = []
    for label, fields in _text(language)["trust_items"]:
        trust_cards.append(
            f"""
<div class="trust-card">
  <div class="trust-label">{escape(label)}</div>
  <div class="trust-fields">{escape(fields)}</div>
</div>
            """
        )
    render_html(
        f"""
<section class="section trust-panel">
  <h2 class="section-title">{escape(_text(language)["trust_title"])}</h2>
  <p class="trust-body">{escape(_text(language)["trust_body"])}</p>
  <div class="trust-grid">{''.join(trust_cards)}</div>
</section>
        """
    )


def render_landing_footer(language: str) -> None:
    render_html(f"<footer class=\"landing-footer\">{escape(_text(language)['footer'])}</footer>")


def render_landing_page(language: str = "zh", asset_count: int = 3, source_count: int = 2) -> None:
    render_landing_styles()
    render_hero_section(language)
    render_floating_stats(language, asset_count=asset_count, source_count=source_count)
    render_bento_grid(language)
    render_workflow_section(language)
    render_data_trust_section(language)
    render_landing_footer(language)
