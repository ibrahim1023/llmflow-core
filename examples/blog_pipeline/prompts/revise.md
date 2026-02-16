You are revising a blog draft.

Topic: {{ inputs.topic }}
Audience: {{ inputs.audience }}
Strengths: {{ inputs.strengths | join(", ") }}
Weaknesses: {{ inputs.weaknesses | join(", ") }}
Revision goals: {{ inputs.revision_goals | join(", ") }}

Return JSON with:
- title: string
- summary: string
- body: string
