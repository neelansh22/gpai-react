export const cases = [
  {
    id: "CS-1042",
    title: "The intermittent warning",
    category: "Product support",
    outcome: "Resolved",
    excerpt: "Customer: My Aster E4 keeps showing a battery warning after overnight charging.\nAgent: The diagnostic scan returned code B142. We replaced the 12V battery and the warning cleared.",
  },
  {
    id: "CS-1088",
    title: "The warning returns",
    category: "Technical support",
    outcome: "Escalated",
    excerpt: "Customer: The battery warning is back on my Aster E4, even after the 12V battery was replaced.\nAgent: The scan shows B142 again. Battery replacement did not resolve it, so I am escalating for further diagnosis.",
  },
  {
    id: "CS-1126",
    title: "A software resolution",
    category: "Repair enquiry",
    outcome: "Resolved",
    excerpt: "Customer: My Aster E4 shows a battery warning on startup.\nAgent: We found code B142 and installed the controller software update. The warning cleared after the update.",
  },
];

export const nodes = [
  { id: "vehicle", label: "Aster E4", type: "Product", x: 150, y: 120, description: "A fictional vehicle model mentioned across the example conversations.", cases: ["CS-1042", "CS-1088", "CS-1126"] },
  { id: "warning", label: "Battery warning", type: "Symptom", x: 380, y: 215, description: "A recurring warning reported by customers. Its presence does not establish a cause.", cases: ["CS-1042", "CS-1088", "CS-1126"] },
  { id: "code", label: "B142", type: "Diagnostic", x: 620, y: 100, description: "A fictional diagnostic code found in all three example calls.", cases: ["CS-1042", "CS-1088", "CS-1126"] },
  { id: "battery", label: "12V battery", type: "Component", x: 155, y: 340, description: "A component replaced in two examples, with different outcomes.", cases: ["CS-1042", "CS-1088"] },
  { id: "replace", label: "Battery replacement", type: "Action", x: 380, y: 390, description: "An attempted repair. One call reports success; another reports failure.", cases: ["CS-1042", "CS-1088"] },
  { id: "update", label: "Software update", type: "Action", x: 650, y: 330, description: "A controller software update described in one resolution.", cases: ["CS-1126"] },
  { id: "escalation", label: "Further diagnosis", type: "Outcome", x: 600, y: 480, description: "An escalation for further diagnosis after an unsuccessful repair.", cases: ["CS-1088"] },
];

export const edges = [
  { id: "e1", from: "vehicle", to: "warning", label: "reported on", caseId: "CS-1042", quote: "My Aster E4 keeps showing a battery warning", status: "confirmed" },
  { id: "e2", from: "warning", to: "code", label: "observed with", caseId: "CS-1042", quote: "The diagnostic scan returned code B142", status: "confirmed" },
  { id: "e3", from: "battery", to: "replace", label: "component in", caseId: "CS-1042", quote: "We replaced the 12V battery", status: "confirmed" },
  { id: "e4", from: "replace", to: "warning", label: "cleared in one case", caseId: "CS-1042", quote: "We replaced the 12V battery and the warning cleared", status: "confirmed" },
  { id: "e5", from: "replace", to: "escalation", label: "failed in one case", caseId: "CS-1088", quote: "Battery replacement did not resolve it, so I am escalating", status: "proposed" },
  { id: "e6", from: "update", to: "warning", label: "cleared in one case", caseId: "CS-1126", quote: "The warning cleared after the update", status: "proposed" },
  { id: "e7", from: "code", to: "update", label: "observed before", caseId: "CS-1126", quote: "We found code B142 and installed the controller software update", status: "confirmed" },
];
