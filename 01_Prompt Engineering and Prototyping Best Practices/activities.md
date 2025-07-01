# Session 1 – Vibe Check: Activity #1 & Discussion

## Introduction

This document summarizes my "vibe check" evaluation for Session 1 of the AI Makerspace Engineering Bootcamp. I tested my deployed LLM-powered chat application using the required prompts, evaluating each for clarity, accuracy, and overall system performance.

---

### 🔹 Question 1

**Prompt**:  
Explain the concept of object-oriented programming in simple terms to a complete beginner.

**Aspect Tested**:  
Clarity / Focus / Conceptual Simplification

**System Performance Evaluation**:  
The system provided a clear and concise response, suitable for a complete beginner. Notably, responses were longer and more thorough when selecting the `expert programmer` developer message versus a generic `helpful assistant`.  
**Strengths:** Clarity and structure.  
**Weaknesses:** The length may be too much for some absolute beginners.

---

### 🔹 Question 2

**Prompt**:  
Read the following essay and provide a concise summary of the key points.

**Aspect Tested**:  
Conceptual Accuracy / Summarization / Comprehension

**System Performance Evaluation**:  
The system accurately summarized the essay's main points without omitting any crucial details. When prompted again for an even more concise summary, the system delivered as expected.  
**Strengths:** Consistency in capturing key points.  
**Weaknesses:** Could occasionally be more concise.

---

### 🔹 Question 3

**Prompt**:  
Write a short, straightforward post for the role of biomathematics apprenticeship.

**Aspect Tested**:  
Coherence / Tone / Precision

**System Performance Evaluation**:  
Initially, the system's performance was only satisfactory. With additional context and a more tailored developer message, the tone and precision improved noticeably.  
**Strengths:** Adaptability with more context.  
**Weaknesses:** Initial vagueness.

---

### 🔹 Question 4

**Prompt**:  
If a store sells apples in packs of 4 and oranges in packs of 3, how many packs of each do I need to buy to get exactly 13 apples and 11 oranges?

**Aspect Tested**:  
Reasoning / Non-solution / Chain-of-Thought

**System Performance Evaluation**:  
The prompt was a trick problem with no valid solution. The system correctly identified this, explained why, and suggested asking for clarification or more details.  
**Strengths:** Strong reasoning and error handling.  
**Weaknesses:** None observed in this case.

---

### 🔹 Question 5

**Prompt**:  
Rewrite the Zen of Python in a professional, formal tone.

**Aspect Tested**:  
Style-guide Adherence / Tone Conversion

**System Performance Evaluation**:  
The system converted the Zen of Python to a formal style, maintaining clarity and flow throughout.  
**Strengths:** Faithfulness to original content and clear conversion.  
**Weaknesses:** Minor risk of losing the original’s poetic tone.

---

## ❓ Discussion Question #1

**Prompt**:  
What are some limitations of vibe checking as an evaluation tool?

**Answer**:  
'Vibe checking' is an informal, unstructured, and non-comprehensive evaluation of LLM-powered systems, meant to quickly spot obvious failures. Its limitations include:
- Subjectivity
- Lack of reproducibility
- No quantitative metrics
- Only surface-level coverage

For more robust evaluation, a combination of vibe checks and formal, quantitative methods is needed.

---

## Conclusion

This vibe check provided an initial baseline for my application. Going forward, I plan to incorporate more targeted developer prompts, add automated testing for edge cases, and collect user feedback for deeper evaluation.
