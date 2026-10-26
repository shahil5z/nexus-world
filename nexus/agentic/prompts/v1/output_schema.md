Output schemas are enforced with structured outputs:
- Supervisor: ScenarioIntent (nexus/agentic/schemas.py).
- Model Critic: CriticOutput {verdict, reasons, evidence_ids}.
- Explanation: Explanation {executive_result, key_outcomes, scenario, baseline, counterfactual, uncertainty, key_modeled_drivers, critique, assumptions, limitations, recommendation, evidence_ids_used}.
