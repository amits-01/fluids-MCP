# AI Usage Disclosure

This note transparently documents where and how 
AI assistance was used during this assignment.

---

## Where AI Was Used

### 1. README and Documentation
AI was used to draft README.md, ARCHITECTURE.md, and RATIONALE.md.

Writing clear technical documentation is a skill in itself, but 
it is not the core competency being evaluated here. Using AI to 
produce well-structured documentation allowed me to focus my 
time on the architectural decisions, implementation correctness, 
and debugging.

### 2. Chat UI (ui/index.html)
AI was used to generate the HTML/CSS/JS for the chat interface.

Frontend development is not my primary domain. The chat UI is 
an operational endpoint for manual testing and not a deliverable 
being evaluated for design quality. Using AI here saved time without 
compromising the core work, and also made the output more clean and appealing.

---

## Where AI Was NOT Used

### 1. Architecture Design
The 3-tier hierarchy, dynamic tool registration pattern, 
description driven LLM routing, and tier boundary decisions 
were my own. These came from understanding the problem statement 
and reasoning through the trade-offs independently, and my experience on this domain.

### 2. Core Implementation
All 4 service files were written with AI as a reference tool 
only, similar to using documentation. The actual logic for 
dynamic registration, request routing, graceful degradation, 
and request tracing reflects my own understanding of how these 
systems should work. I also incorporated my implementation from 
what I have already built in fraud detection system under production environment. 

### 3. Test Design
The test cases: routing correctness, registry behavior, 
end-to-end flow, graceful degradation, were designed based 
on what I believed needed validation.

---

## My View on AI-Assisted Development

AI tools are part of modern engineering workflows. Using them 
well means knowing when they accelerate work without 
compromising understanding.

For this assignment, I used AI the same way I would use 
a senior colleague for a code review or documentation pass,
as a support layer, not as the engineer.
