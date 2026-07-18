"""Workflow Stages — Document 06 Section 2.

Defines the 24 End-to-End Constitutional Workflow Stages. Each stage
is a discrete unit of work with Purpose, Office, Agent, Entry
Conditions, Exit Conditions, Validation Rules, Failure Conditions,
and Escalation Rules.

The Discovery Order is the canonical sequence of the 24 stages. It is
NOT a simple sequence — a stage depends on the previous stage and CANNOT
be skipped, abbreviated, or reordered (ORCH-SEQ-002, ORCH-SEQ-003,
WF-PRIN-007).

This is a pure-logic module. The Workflow Engine wraps it with the
runtime state, the audit log, the orchestration state machine, and the
data layer.

Constitutional source:
  - Constitution Articles VI, VII, X, XII, XVII, XIX
  - Document 06 §2.1..2.24 (24 Stages)
  - Document 06 §3.1 (Sequential Execution — ORCH-SEQ-001..003)
  - WF-PRIN-007 (No step may be skipped, abbreviated, or reordered)
  - AC-P3-001 (A workflow can be initiated, executed, transitioned, closed)
  - AC-P3-002 (Discovery Order cannot be skipped/abbreviated/reordered)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Mapping


class StageNumber(int, Enum):
    """The 24 stage numbers of Document 06 §2.

    The enum VALUE is the §2.X number; the enum NAME is the short label.
    """

    S01_INDUSTRIAL_ENVIRONMENT = 1
    S02_INDUSTRIAL_ACTIVITY_DETECTION = 2
    S03_VALIDATED_SIGNAL = 3
    S04_PROBLEM_DEFINITION = 4
    S05_ROOT_CAUSE = 5
    S06_COMMERCIAL_VALUE_CASE = 6
    S07_TECHNOLOGY_CATEGORY = 7
    S08_PRODUCT_DISCOVERY = 8
    S09_REPLACEMENT_ANALYSIS = 9
    S10_KUWAIT_SUITABILITY = 10
    S11_MANUFACTURER_INTELLIGENCE = 11
    S12_COMMERCIAL_EVALUATION = 12
    S13_VERIFICATION = 13
    S14_QUALITY_REVIEW = 14
    S15_HUMAN_APPROVAL = 15
    S16_BUSINESS_DEVELOPMENT = 16
    S17_REGISTRATION = 17
    S18_MARKET_ENTRY = 18
    S19_TENDER_SUPPORT = 19
    S20_PROJECT_SUPPORT = 20
    S21_COMMERCIAL_OUTCOME = 21
    S22_KNOWLEDGE_CAPTURE = 22
    S23_INSTITUTIONAL_MEMORY = 23
    S24_CONTINUOUS_LEARNING = 24


# ---------------------------------------------------------------------------
# Stage spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageSpec:
    """The constitutional spec of one stage (Document 06 §2.X)."""

    number: StageNumber
    title: str
    purpose: str
    responsible_office: str
    responsible_agent: str
    required_inputs: tuple[str, ...]
    produced_outputs: tuple[str, ...]
    entry_conditions: tuple[str, ...]
    exit_conditions: tuple[str, ...]
    validation_rules: tuple[str, ...]
    failure_conditions: tuple[str, ...]
    escalation_rules: tuple[str, ...]


# ---------------------------------------------------------------------------
# 24 Stage specifications (Document 06 §2.1..2.24, condensed)
# ---------------------------------------------------------------------------


STAGES: Mapping[StageNumber, StageSpec] = {
    StageNumber.S01_INDUSTRIAL_ENVIRONMENT: StageSpec(
        number=StageNumber.S01_INDUSTRIAL_ENVIRONMENT,
        title="Industrial Environment",
        purpose=(
            "Maintain the constitutional environmental picture that defines the "
            "geography, regulation, economy, and sector structure relevant to the "
            "System's scope."
        ),
        responsible_office="Industrial Intelligence Office",
        responsible_agent="Industrial Environment Monitor Agent",
        required_inputs=(
            "Authoritative public sources",
            "Regulatory publications",
            "Sector reports",
            "Previous Environmental Profile",
        ),
        produced_outputs=("Environmental Profile Update",),
        entry_conditions=(
            "The Environmental Profile exists or is being created for a sector or geography",
            "Refresh is due",
        ),
        exit_conditions=(
            "The Environmental Profile is updated, sourced, and recorded",
            "The update is logged",
        ),
        validation_rules=("Source citation", "Date", "Sector scope", "Constitutional register check"),
        failure_conditions=("Sources unavailable", "Sector outside scope", "Date missing"),
        escalation_rules=(
            "Material change in regulation or sector structure",
            "Sector outside scope",
            "Contradictory sources",
        ),
    ),
    StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION: StageSpec(
        number=StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION,
        title="Industrial Activity Detection",
        purpose="Detect and characterise Industrial Activity within the constitutional scope.",
        responsible_office="Industrial Intelligence Office",
        responsible_agent="Industrial Activity Detection Agent",
        required_inputs=("Environmental Profile", "Authoritative sources", "Sector publications", "Existing Industrial Activity records"),
        produced_outputs=("Industrial Activity Record with classification",),
        entry_conditions=("A potential Industrial Activity is identified within constitutional scope",),
        exit_conditions=(
            "The activity is classified (Confirmed, Announced, Probable, or Speculative)",
            "Recorded",
            "Either rejected or routed for further analysis",
        ),
        validation_rules=("Source citation", "Date", "Classification rationale", "Sector scope"),
        failure_conditions=("Activity outside scope", "Speculative without evidence", "Duplicate of existing record"),
        escalation_rules=("Material new project, tender, or regulatory change", "Conflict with existing record", "Sector uncertainty"),
    ),
    StageNumber.S03_VALIDATED_SIGNAL: StageSpec(
        number=StageNumber.S03_VALIDATED_SIGNAL,
        title="Validated Signal",
        purpose=(
            "Confirm that a detected Industrial Activity has cleared the Preliminary "
            "Evidence Review of Stage 6 of the Discovery Order at the Industrial "
            "Intelligence layer."
        ),
        responsible_office="Industrial Intelligence Office",
        responsible_agent="Validated Signal Agent; with the Preliminary Evidence Reviewer Agent on the Preliminary Review",
        required_inputs=("Industrial Activity Record", "Source citations", "Preliminary Evidence Review criteria"),
        produced_outputs=("Validated Signal Record", "Preliminary Evidence Review Record"),
        entry_conditions=("An Industrial Activity Record has been produced and is in scope",),
        exit_conditions=("The signal is declared Validated or rejected", "The outcome is recorded"),
        validation_rules=("Preliminary Evidence Review completed", "Classification confirmed", "Source citation verified"),
        failure_conditions=("Activity not credible", "Sources conflicting", "Information insufficient"),
        escalation_rules=("Inability to confirm credibility", "Conflicting sources", "Constitutional concern"),
    ),
    StageNumber.S04_PROBLEM_DEFINITION: StageSpec(
        number=StageNumber.S04_PROBLEM_DEFINITION,
        title="Problem Definition",
        purpose="Convert the Validated Signal into a defined Problem or Need.",
        responsible_office="Opportunity Intelligence Office",
        responsible_agent="Problem and Need Definition Agent",
        required_inputs=("Validated Signal Record", "Stakeholder statements", "Sector sources", "Existing Problem or Need Statements"),
        produced_outputs=("Problem or Need Statement", "Information gap record"),
        entry_conditions=("A Validated Signal is in scope", "The constitutional scope is satisfied"),
        exit_conditions=("The Problem or Need is defined and recorded", "Information gaps are documented"),
        validation_rules=("Source citation", "Stakeholder attribution", "Date", "Constitutional scope check"),
        failure_conditions=("Signal not validated", "Problem already defined", "Outside scope"),
        escalation_rules=("Inability to define the problem", "Conflicting stakeholder statements", "Constitutional concern"),
    ),
    StageNumber.S05_ROOT_CAUSE: StageSpec(
        number=StageNumber.S05_ROOT_CAUSE,
        title="Root Cause",
        purpose="Establish the underlying Root Cause of the defined Problem or Need.",
        responsible_office="Opportunity Intelligence Office",
        responsible_agent="Root Cause Analysis Agent",
        required_inputs=("Problem or Need Statement", "Operational data", "Failure data", "Expert sources"),
        produced_outputs=("Root Cause Statement", "Alternative-cause register"),
        entry_conditions=("A Problem or Need is defined", "The Root Cause analysis is in scope"),
        exit_conditions=("The Root Cause is established", "Alternatives are recorded", "The statement is logged"),
        validation_rules=("Method used", "Data sources", "Alternatives considered", "Specialist verification"),
        failure_conditions=("Problem not defined", "Insufficient data", "Method not constitutional"),
        escalation_rules=("Conflicting causal theories", "Absence of operational data", "Constitutional concern"),
    ),
    StageNumber.S06_COMMERCIAL_VALUE_CASE: StageSpec(
        number=StageNumber.S06_COMMERCIAL_VALUE_CASE,
        title="Commercial Value Case",
        purpose="Convert the defined Problem and Root Cause into a Commercial Value Case.",
        responsible_office="Opportunity Intelligence Office",
        responsible_agent="Commercial Value Definition Agent",
        required_inputs=("Problem or Need Statement", "Root Cause Statement", "Customer or market sources", "Benchmark data"),
        produced_outputs=("Value Case", "Baseline record", "Measurement method", "Uncertainty record"),
        entry_conditions=("A Root Cause is established", "The Value Case is in scope"),
        exit_conditions=(
            "The Value Case is established",
            "The baseline and measurement method are recorded",
            "Uncertainty is documented",
        ),
        validation_rules=("Baseline", "Measurement method", "Source citation", "Assumptions", "Uncertainty", "Specialist verification"),
        failure_conditions=("Root Cause not established", "Baseline missing", "Measurement method invalid"),
        escalation_rules=("Inability to establish a baseline", "Conflicting measurement methods", "Constitutional concern about the Value Qualification Rule"),
    ),
    StageNumber.S07_TECHNOLOGY_CATEGORY: StageSpec(
        number=StageNumber.S07_TECHNOLOGY_CATEGORY,
        title="Technology Category",
        purpose="Identify the Technology Category capable of addressing the established Value Case.",
        responsible_office="Technology Intelligence Office",
        responsible_agent="Technology Category Analyst Agent",
        required_inputs=("Value Case", "Sector technology sources", "Standards bodies", "Existing Technology Category Analyses"),
        produced_outputs=("Technology Category Analysis", "Alternatives considered"),
        entry_conditions=("A Value Case is established", "The category analysis is in scope"),
        exit_conditions=("The Technology Category is identified", "Alternatives are recorded", "The analysis is logged"),
        validation_rules=("Source citation", "Category fit rationale", "Alternatives considered", "Specialist verification"),
        failure_conditions=("Value Case not established", "Category outside scope", "No viable category"),
        escalation_rules=("Inability to identify a viable category", "Conflict with constitutional principles", "Constitutional concern"),
    ),
    StageNumber.S08_PRODUCT_DISCOVERY: StageSpec(
        number=StageNumber.S08_PRODUCT_DISCOVERY,
        title="Product Discovery",
        purpose="Identify candidate Products and Solutions within the defined Technology Category.",
        responsible_office="Technology Intelligence Office",
        responsible_agent="Product Analyst Agent",
        required_inputs=("Technology Category Analysis", "Product data sheets", "Standards and certifications", "Independent test data", "Constitutional register check"),
        produced_outputs=("Product Analysis", "Evaluation criteria", "Performance data", "Claim classifications"),
        entry_conditions=("A Technology Category is identified", "The Product analysis is in scope"),
        exit_conditions=("The Product Analysis is complete", "Claim classifications are recorded", "The analysis is logged"),
        validation_rules=("Source citation", "Evaluation criteria", "Performance data", "Standards and certifications", "Specialist verification", "Constitutional register check"),
        failure_conditions=("Category not identified", "Product from a Restricted Entity", "Insufficient data"),
        escalation_rules=("Conflict between Product claims and independent data", "Missing standards data", "Constitutional concern"),
    ),
    StageNumber.S09_REPLACEMENT_ANALYSIS: StageSpec(
        number=StageNumber.S09_REPLACEMENT_ANALYSIS,
        title="Replacement Analysis",
        purpose="Determine the current solution and produce the Comparative Analysis with the Value Qualification Rule applied.",
        responsible_office="Technology Intelligence Office",
        responsible_agent="Replacement and Comparative Analysis Agent",
        required_inputs=("Product Analysis", "Incumbent solution data", "Operational data", "Benchmark sources", "Constitutional register check"),
        produced_outputs=("Comparative Analysis", "Baseline", "Measurement method", "Classification under the Value Qualification Rule"),
        entry_conditions=("A Product Analysis is complete", "The comparative analysis is in scope"),
        exit_conditions=(
            "The Comparative Analysis is complete",
            "The Value Qualification Rule is applied",
            "The classification is recorded",
            "The result is verified",
        ),
        validation_rules=("Baseline", "Measurement method", "Source citation", "Assumptions", "Uncertainty", "Independent Final Verification"),
        failure_conditions=("Product Analysis incomplete", "Baseline missing", "Value Qualification Rule unmet"),
        escalation_rules=("Comparative case below threshold", "Conflicting baseline data", "Strategic exception request", "Constitutional concern"),
    ),
    StageNumber.S10_KUWAIT_SUITABILITY: StageSpec(
        number=StageNumber.S10_KUWAIT_SUITABILITY,
        title="Kuwait Suitability",
        purpose="Review the proposed solution against technical, standards, environmental, and Kuwait-specific requirements.",
        responsible_office="Technology Intelligence Office",
        responsible_agent="Kuwait Suitability Reviewer Agent",
        required_inputs=("Comparative Analysis", "Kuwait regulatory sources", "Standards bodies", "Environmental data", "Constitutional register check"),
        produced_outputs=("Suitability Review", "Standards and certifications summary", "Suitability gap record"),
        entry_conditions=("A Comparative Analysis is complete", "The suitability review is in scope"),
        exit_conditions=("The Suitability Review is complete", "Gaps are recorded", "The review is logged"),
        validation_rules=("Source citation", "Standard reference", "Date", "Specialist verification", "Constitutional register check"),
        failure_conditions=("Comparative Analysis incomplete", "Regulatory source missing", "Gap unresolved"),
        escalation_rules=("Regulatory conflict", "Missing standard", "Environmental non-conformance", "Constitutional concern"),
    ),
    StageNumber.S11_MANUFACTURER_INTELLIGENCE: StageSpec(
        number=StageNumber.S11_MANUFACTURER_INTELLIGENCE,
        title="Manufacturer Intelligence",
        purpose="Profile, assess, and compare candidate Manufacturers against constitutional Manufacturer criteria.",
        responsible_office="Manufacturer Intelligence Office",
        responsible_agent="Manufacturer Profiler Agent; Manufacturer Credibility Analyst Agent; Manufacturer Comparison Agent",
        required_inputs=("Comparative Analysis", "Manufacturer sources", "Certification bodies", "Register checks", "Risk and Compliance input"),
        produced_outputs=("Manufacturer Profile", "Manufacturer Credibility Assessment", "Manufacturer Comparison Report"),
        entry_conditions=("A Comparative Analysis is complete", "Candidate Manufacturers are identified", "The assessment is in scope"),
        exit_conditions=(
            "The Manufacturer Profile is current",
            "The Credibility Assessment is multi-dimensional",
            "The Comparison Report is vendor-neutral and multi-criteria",
        ),
        validation_rules=("Source citation", "Multi-dimensional scorecard", "Trade-off analysis", "Specialist verification", "Constitutional register check"),
        failure_conditions=("Profile stale", "Sources unreliable", "Assessment missing dimensions", "Comparison single-criterion"),
        escalation_rules=("Material adverse finding", "Conflicting data", "Missing Represented Principal", "Restricted Entity", "Constitutional concern"),
    ),
    StageNumber.S12_COMMERCIAL_EVALUATION: StageSpec(
        number=StageNumber.S12_COMMERCIAL_EVALUATION,
        title="Commercial Evaluation",
        purpose="Evaluate the commercial case for the Opportunity against the Constitutional Commercial Principles.",
        responsible_office="Commercial Development Office",
        responsible_agent="Commercial Evaluation Agent",
        required_inputs=("Verified Opportunity case", "Market data", "Competitor data", "Agency data", "Constitutional register check"),
        produced_outputs=("Commercial Evaluation", "Multi-dimensional scorecard", "Risk register reference"),
        entry_conditions=("The Opportunity case has cleared the Verification Office", "The Commercial Evaluation is in scope"),
        exit_conditions=("The Commercial Evaluation is complete", "The scorecard is recorded", "The evaluation is logged"),
        validation_rules=("Source citation", "Multi-dimensional scorecard", "Assumptions", "Uncertainty", "Specialist verification", "Constitutional register check"),
        failure_conditions=("Opportunity case not verified", "Sources unreliable", "Constitutional register conflict"),
        escalation_rules=("Return below the approved probability-of-success threshold", "Commercial viability gap", "Constitutional concern"),
    ),
    StageNumber.S13_VERIFICATION: StageSpec(
        number=StageNumber.S13_VERIFICATION,
        title="Verification",
        purpose="Provide the constitutional Independent Verification of the Opportunity case.",
        responsible_office="Verification Office",
        responsible_agent="Independent Final Verifier Agent; with the Preliminary Evidence Reviewer Agent and the Specialist Verifier Agent",
        required_inputs=("Complete material case", "Source citations", "Producer's verification record", "Constitutional register check"),
        produced_outputs=("Preliminary Evidence Review Record", "Specialist Verification Record", "Independent Final Verification Record", "Claim Classification Record"),
        entry_conditions=("The Opportunity case is complete", "Independent Final Verification is mandated by Stage 15 of the Discovery Order"),
        exit_conditions=("The verification is complete", "The outcome is recorded", "The record is logged"),
        validation_rules=("Source citation", "Verification criteria", "Outcome", "Reason for any qualification or rejection", "Second reviewer for material claims"),
        failure_conditions=("Producer is the verifier", "Insufficient evidence", "Not in scope"),
        escalation_rules=("Producer disagreement", "Conflicting evidence", "Suspicion of fabrication", "Constitutional concern"),
    ),
    StageNumber.S14_QUALITY_REVIEW: StageSpec(
        number=StageNumber.S14_QUALITY_REVIEW,
        title="Quality Review",
        purpose="Review the verified Opportunity case for quality, completeness, and constitutional compliance at the Office level.",
        responsible_office="Quality Assurance Office",
        responsible_agent="Quality Reviewer Agent; with the Standards Compliance Agent",
        required_inputs=("Verified Opportunity case", "Quality criteria", "Verification record", "Constitutional register check"),
        produced_outputs=("Quality Review Record", "Standards Compliance Report", "Rework request"),
        entry_conditions=("A material output is in scope", "Quality review is required"),
        exit_conditions=("The review is complete", "The findings are recorded", "The rework request, if any, is issued", "The record is logged"),
        validation_rules=("Criteria", "Findings", "Rework request", "Cross-validation"),
        failure_conditions=("Output not in scope", "Criteria missing", "Not material"),
        escalation_rules=("Repeated rework", "Concealment of quality issue", "Constitutional concern"),
    ),
    StageNumber.S15_HUMAN_APPROVAL: StageSpec(
        number=StageNumber.S15_HUMAN_APPROVAL,
        title="Human Approval",
        purpose="Submit the Opportunity case to the appropriate Authorised Human Authority for a Decision.",
        responsible_office="Originating Office; Authorised Human Authority",
        responsible_agent="Originating Principal Agent; with the Human Escalation Coordination Agent",
        required_inputs=("Verified Opportunity case", "Quality Review", "Decision Class", "Required Approver Role", "Constitutional Compliance Attestation"),
        produced_outputs=("Approval Request", "Approval Package", "Approval or Rejection", "Decision Log Entry"),
        entry_conditions=("The Opportunity case is verified", "The Decision Class is determined", "The Required Approver Role is identified"),
        exit_conditions=("The approval is granted, qualified, or rejected", "The Decision is recorded", "The Decision Log Entry is created"),
        validation_rules=("Decision Class", "Approver identification", "Conditions", "Duration", "Revocation conditions", "Separation of duties"),
        failure_conditions=("No explicit approver", "Inferred approval", "Self-approval", "Absence of constitutional compliance attestation"),
        escalation_rules=("Unacknowledged approval request", "Conflicting decisions", "Material change in circumstances", "Constitutional concern"),
    ),
    StageNumber.S16_BUSINESS_DEVELOPMENT: StageSpec(
        number=StageNumber.S16_BUSINESS_DEVELOPMENT,
        title="Business Development",
        purpose="Support business development engagement with the counterparty under Human Approval.",
        responsible_office="Commercial Development Office",
        responsible_agent="Business Development Agent; with the Relationship Management Office and the Pricing and Margin Analyst Agent",
        required_inputs=("Approved Opportunity", "Commercial Model Options", "Engagement material", "Human Approval reference", "Constitutional register check"),
        produced_outputs=("Engagement Material", "Meeting Brief", "Follow-up Plan", "Pipeline Update", "Initial Communication"),
        entry_conditions=("The Opportunity is approved for contact", "The engagement scope is approved", "The constitutional register check is clear"),
        exit_conditions=("The engagement is recorded", "The contact is approved", "The outcome is logged", "The pipeline is updated"),
        validation_rules=("Engagement material approved", "Human Approval reference present", "Constitutional register check clear", "Counterparty profile current"),
        failure_conditions=("No Human Approval", "Constitutional register conflict", "Counterparty profile stale"),
        escalation_rules=("Counterparty conflict with Registers", "Unsolicited commitment request", "Pattern of unapproved engagement", "Constitutional concern"),
    ),
    StageNumber.S17_REGISTRATION: StageSpec(
        number=StageNumber.S17_REGISTRATION,
        title="Registration",
        purpose="Support manufacturer, partner, and product registration processes.",
        responsible_office="Registration and Market Entry Office",
        responsible_agent="Registration Coordinator Agent; with the Prequalification Agent",
        required_inputs=("Approved Opportunity", "Registration requirements", "Manufacturer Profile", "Document sources", "Human Approval reference", "Constitutional register check"),
        produced_outputs=("Registration Status Report", "Registration Dossier"),
        entry_conditions=("A registration activity is in scope", "Requirements are identified"),
        exit_conditions=("The dossier is prepared", "The filing is approved", "The status is updated", "The record is logged"),
        validation_rules=("Source citation", "Document reference", "Date", "Human Approval reference", "Constitutional register check"),
        failure_conditions=("Requirements unclear", "Document missing", "Human Approval missing", "Constitutional register conflict"),
        escalation_rules=("Expiring registration", "Missing document", "Regulator query", "Constitutional concern"),
    ),
    StageNumber.S18_MARKET_ENTRY: StageSpec(
        number=StageNumber.S18_MARKET_ENTRY,
        title="Market Entry",
        purpose="Design market-entry options for new Manufacturers, products, or territories.",
        responsible_office="Registration and Market Entry Office",
        responsible_agent="Market Entry Strategy Agent",
        required_inputs=("Approved Opportunity", "Manufacturer Profile", "Regulatory sources", "Channel sources", "Risk and Compliance input"),
        produced_outputs=("Market Entry Options Report", "Risk map", "Stakeholder map"),
        entry_conditions=("A market-entry initiative is in scope", "Regulatory and channel sources are available"),
        exit_conditions=("The options report is delivered", "The risk map is recorded", "The report is logged"),
        validation_rules=("Source citation", "Stakeholder map", "Risk map", "Constitutional register check"),
        failure_conditions=("Manufacturer Profile missing", "Regulatory source missing", "Channel source missing", "Constitutional register conflict"),
        escalation_rules=("Regulatory barrier", "Conflicting channel options", "Unresolved representation status", "Constitutional concern"),
    ),
    StageNumber.S19_TENDER_SUPPORT: StageSpec(
        number=StageNumber.S19_TENDER_SUPPORT,
        title="Tender Support",
        purpose="Support tender qualification, quotation preparation, and tender submission.",
        responsible_office="Tender and Project Intelligence Office",
        responsible_agent="Tender Monitor Agent; Tender Qualification Agent; Quotation Support Agent",
        required_inputs=("Approved Opportunity", "Procurement sources", "Capability records", "Manufacturer Comparison", "Pricing and Margin Analysis", "Constitutional register check"),
        produced_outputs=("Tender Record", "Tender Qualification Report", "Quotation Dossier", "Tender Submission Dossier"),
        entry_conditions=("A tender is in scope", "Capability records are available", "The constitutional register check is clear"),
        exit_conditions=("The tender is monitored", "The qualification is recorded", "The Quotation Dossier is prepared", "The submission is approved"),
        validation_rules=("Source citation", "Fit assessment", "Risk assessment", "Commercial assessment", "Pricing model", "Independent Final Verification", "Human Approval reference", "Constitutional register check"),
        failure_conditions=("Tender not qualified", "Pricing missing", "Verification missing", "Human Approval missing", "Constitutional register conflict"),
        escalation_rules=("Capability gap", "Register conflict", "Commercial infeasibility", "Margin below floor", "Missing technical evidence", "Constitutional concern"),
    ),
    StageNumber.S20_PROJECT_SUPPORT: StageSpec(
        number=StageNumber.S20_PROJECT_SUPPORT,
        title="Project Support",
        purpose="Monitor awarded projects through execution and identify after-sales opportunities.",
        responsible_office="Tender and Project Intelligence Office",
        responsible_agent="Project Monitor Agent",
        required_inputs=("Awarded Project", "Project award records", "Performance data", "Counterparty communications", "Constitutional register check"),
        produced_outputs=("Project Status Report", "Issue Log", "After-Sales Opportunity Identification"),
        entry_conditions=("An awarded project is in scope", "Performance data is available"),
        exit_conditions=("The status report is delivered", "Issues are logged", "After-sales opportunities are identified", "The report is logged"),
        validation_rules=("Source citation", "Performance data", "Date", "Specialist verification", "Constitutional register check"),
        failure_conditions=("Award record missing", "Performance data missing", "Constitutional register conflict"),
        escalation_rules=("Milestone slip", "Commercial dispute", "Safety or environmental incident", "Constitutional concern"),
    ),
    StageNumber.S21_COMMERCIAL_OUTCOME: StageSpec(
        number=StageNumber.S21_COMMERCIAL_OUTCOME,
        title="Commercial Outcome",
        purpose="Track the realised commercial outcome of the Opportunity and convert it into institutional learning.",
        responsible_office="Performance and Learning Office",
        responsible_agent="Commercial Outcomes Analyst Agent",
        required_inputs=("Closed Opportunity", "Commercial records", "Performance data", "Constitutional provisions"),
        produced_outputs=("Commercial Outcome", "Win/Loss Analysis", "Margin Analysis", "Lesson Learned"),
        entry_conditions=("The Opportunity has reached a governed Final Disposition",),
        exit_conditions=("The Commercial Outcome is recorded", "The Win/Loss Analysis is complete", "The Lesson Learned is captured"),
        validation_rules=("Outcome reference", "Reason", "Date", "Cross-validation"),
        failure_conditions=("Outcome not in scope", "Data missing", "Not material"),
        escalation_rules=("Material adverse outcome", "Pattern of loss", "Constitutional concern"),
    ),
    StageNumber.S22_KNOWLEDGE_CAPTURE: StageSpec(
        number=StageNumber.S22_KNOWLEDGE_CAPTURE,
        title="Knowledge Capture",
        purpose="Capture the Opportunity as institutional knowledge, including negative history, and preserve it permanently.",
        responsible_office="Knowledge and Institutional Memory Office",
        responsible_agent="Knowledge Base Curator Agent; Lessons Learned Analyst Agent",
        required_inputs=("Opportunity", "Verified findings", "Commercial Outcome", "Reasons for status", "Lesson Learned"),
        produced_outputs=("Knowledge Record", "Institutional Memory Entry", "Lesson Learned Record"),
        entry_conditions=("The Opportunity has reached a governed Final Disposition or a material change in status",),
        exit_conditions=("The Knowledge Record is captured", "The Institutional Memory Entry is preserved", "The Lesson Learned is indexed"),
        validation_rules=("Source citation", "Provenance", "Verification reference", "Retention class"),
        failure_conditions=("Outcome not in scope", "Data missing", "Lesson not captured"),
        escalation_rules=("Material lesson not captured", "Pattern of failure", "Constitutional concern"),
    ),
    StageNumber.S23_INSTITUTIONAL_MEMORY: StageSpec(
        number=StageNumber.S23_INSTITUTIONAL_MEMORY,
        title="Institutional Memory",
        purpose="Preserve the Institutional Memory of the Opportunity and ensure its long-term availability and auditability.",
        responsible_office="Knowledge and Institutional Memory Office",
        responsible_agent="Institutional Memory Manager Agent",
        required_inputs=("Knowledge Record", "Institutional Memory Entry", "Records Retention class"),
        produced_outputs=("Institutional Memory Index update", "Retention Report"),
        entry_conditions=("An Institutional Memory event is in scope",),
        exit_conditions=("The index is updated", "The retention report is delivered", "The record is preserved"),
        validation_rules=("Record reference", "Retention class", "Provenance", "Cross-validation"),
        failure_conditions=("Record not in scope", "Retention class missing", "Provenance weak"),
        escalation_rules=("Missing record", "Retention violation", "Provenance loss", "Constitutional concern"),
    ),
    StageNumber.S24_CONTINUOUS_LEARNING: StageSpec(
        number=StageNumber.S24_CONTINUOUS_LEARNING,
        title="Continuous Learning",
        purpose="Convert verified outcomes into organisational learning and coordinate Learning updates under constitutional constraints.",
        responsible_office="Performance and Learning Office",
        responsible_agent="Learning Coordination Agent",
        required_inputs=("Learning proposal", "Constitutional impact assessment", "Performance data"),
        produced_outputs=("Learning Update", "Learning Update Record"),
        entry_conditions=("A learning proposal is in scope", "The proposal is reviewed"),
        exit_conditions=("The proposal is approved, qualified, or rejected", "The record is logged"),
        validation_rules=("Proposal reference", "Constitutional impact", "Date", "Constitutional compliance review"),
        failure_conditions=("Proposal not in scope", "Constitutional impact", "Bias signal", "Not material"),
        escalation_rules=("Constitutional impact", "Bias signal", "Unintended drift", "Constitutional concern"),
    ),
}


# ---------------------------------------------------------------------------
# Discovery Order — the canonical sequence
# ---------------------------------------------------------------------------

DISCOVERY_ORDER: tuple[StageNumber, ...] = (
    StageNumber.S01_INDUSTRIAL_ENVIRONMENT,
    StageNumber.S02_INDUSTRIAL_ACTIVITY_DETECTION,
    StageNumber.S03_VALIDATED_SIGNAL,
    StageNumber.S04_PROBLEM_DEFINITION,
    StageNumber.S05_ROOT_CAUSE,
    StageNumber.S06_COMMERCIAL_VALUE_CASE,
    StageNumber.S07_TECHNOLOGY_CATEGORY,
    StageNumber.S08_PRODUCT_DISCOVERY,
    StageNumber.S09_REPLACEMENT_ANALYSIS,
    StageNumber.S10_KUWAIT_SUITABILITY,
    StageNumber.S11_MANUFACTURER_INTELLIGENCE,
    StageNumber.S12_COMMERCIAL_EVALUATION,
    StageNumber.S13_VERIFICATION,
    StageNumber.S14_QUALITY_REVIEW,
    StageNumber.S15_HUMAN_APPROVAL,
    StageNumber.S16_BUSINESS_DEVELOPMENT,
    StageNumber.S17_REGISTRATION,
    StageNumber.S18_MARKET_ENTRY,
    StageNumber.S19_TENDER_SUPPORT,
    StageNumber.S20_PROJECT_SUPPORT,
    StageNumber.S21_COMMERCIAL_OUTCOME,
    StageNumber.S22_KNOWLEDGE_CAPTURE,
    StageNumber.S23_INSTITUTIONAL_MEMORY,
    StageNumber.S24_CONTINUOUS_LEARNING,
)


def assert_total_stages() -> int:
    """Assert the Discovery Order has exactly 24 stages and return the count.

    Used by tests and the Workflow Engine to fail fast on configuration drift.
    """
    assert len(DISCOVERY_ORDER) == 24, (
        f"Discovery Order must have 24 stages (Document 06 §2), got {len(DISCOVERY_ORDER)}"
    )
    assert set(DISCOVERY_ORDER) == set(StageNumber), "Discovery Order must enumerate every StageNumber"
    return 24


def next_stage(current: StageNumber) -> StageNumber | None:
    """Return the next stage in the Discovery Order, or None if at the end."""
    idx = DISCOVERY_ORDER.index(current)
    if idx + 1 >= len(DISCOVERY_ORDER):
        return None
    return DISCOVERY_ORDER[idx + 1]


def previous_stage(current: StageNumber) -> StageNumber | None:
    """Return the previous stage in the Discovery Order, or None if at the start."""
    idx = DISCOVERY_ORDER.index(current)
    if idx == 0:
        return None
    return DISCOVERY_ORDER[idx - 1]


def is_valid_progression(from_stage: StageNumber, to_stage: StageNumber) -> bool:
    """A stage may only proceed to its IMMEDIATE next neighbour in the Discovery Order.

    Skipping, abbreviating, or reordering is REJECTED (WF-PRIN-007,
    ORCH-SEQ-002, ORCH-SEQ-003). The only legal forward transition is
    `current -> next_stage(current)`.
    """
    nxt = next_stage(from_stage)
    return nxt is not None and to_stage == nxt
