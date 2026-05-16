# Mushir Logic Explained Simply

This document explains how Mushir works in plain language for a non-technical client.

## What Mushir Is

Mushir is a chatbot that helps answer Islamic finance compliance questions using AAOIFI Financial Accounting Standards. It is designed to behave like a careful research assistant: it searches the provided standards, checks whether the information is enough, and gives a cautious answer with references.

Mushir is not a scholar and does not issue binding fatwas. Its answers are informational guidance only. A qualified Sharia scholar should make any final binding decision.

## The Simple Version

When a user asks a question, Mushir follows this process:

1. It checks whether the question is clear enough.
2. If the question is missing an important detail, it asks one follow-up question.
3. If the question is clear, it searches the AAOIFI standards stored in the system.
4. It gives the best-matching text to the AI model.
5. The AI writes an answer using only that retrieved text.
6. Mushir checks that the answer includes real citations from the retrieved standards.
7. If the sources are not strong enough, Mushir says it does not have enough data instead of guessing.

## Example

If a user asks:

> Can I invest in this company?

Mushir should not immediately answer, because it does not know what the company does. Instead, it asks one focused question, such as:

> What type of company or business activity is involved?

If the user asks:

> Is a Murabaha sale with disclosed markup payable over 24 months compliant?

Mushir has enough structure to start checking the standards, so it searches the AAOIFI documents and answers only if it finds useful evidence.

## Why Mushir Asks Follow-Up Questions

Some Islamic finance questions depend heavily on details. A small missing fact can change the answer. Mushir is built to avoid overwhelming the user, so it asks only the most important missing question first.

This helps the user move forward without receiving a long checklist.

## Why Mushir Uses Citations

Every serious answer should point back to the standard it came from. Citations help show:

- which AAOIFI standard was used;
- which section or page supports the answer;
- whether the answer is based on actual source text;
- whether the system had enough evidence.

If Mushir cannot connect the answer to retrieved AAOIFI text, it should not present the answer as grounded.

## What Happens When Mushir Is Unsure

Mushir is intentionally cautious. If the search results are weak, if citations are missing, or if the question goes beyond the stored standards, it returns a controlled message like:

> The retrieved AAOIFI excerpts did not provide a safely citable basis for this answer.

This is a safety feature, not a bug. It prevents confident but unsupported answers.

## What Mushir Refuses To Do

Mushir refuses or limits requests that ask it to:

- issue a binding fatwa;
- replace a Sharia scholar;
- give legal advice;
- give financial advice;
- answer from general AI knowledge without AAOIFI support;
- invent missing standards or citations.

## Languages

Mushir supports English and Arabic. It can also understand mixed Arabic and English questions. Arabic support depends on a multilingual search index, so the system checks that the Arabic and English source material exists before treating Arabic retrieval as ready.

## The User Experience

The user can interact with Mushir through:

- a web chat page at `/chat`;
- a normal API endpoint for one full answer;
- a streaming API endpoint that sends progress-style events.

In the chat interface, the user sees:

- the answer;
- compliance status;
- citations;
- clarification questions when needed;
- safe error messages if something goes wrong.

## The Main Safety Promise

Mushir should be helpful, but not overconfident.

Its core promise is:

> If the AAOIFI evidence is available, Mushir explains it with citations. If the evidence is not available or the question is unclear, Mushir asks one focused question or says it does not have enough data.

## What A Client Should Expect

Mushir is good for:

- early compliance research;
- comparing a transaction idea against available AAOIFI excerpts;
- identifying which standard may be relevant;
- preparing better questions for a scholar or compliance team;
- showing source-backed guidance in English or Arabic.

Mushir is not meant to be the final authority for:

- binding Sharia rulings;
- legal decisions;
- investment recommendations;
- regulatory sign-off;
- cases where the source documents are incomplete.

