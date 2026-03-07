# BharatBuild AI - Correct Fine-tuning Roadmap

## Current Status
- [x] 503 Gold Samples generated
- [ ] Step 1: SFT v1 (gold only)
- [ ] Step 2: Evaluation
- [ ] Step 3: Generate Silver Data
- [ ] Step 4: SFT v2 (gold + silver)
- [ ] Step 5: DPO Training
- [ ] Step 6: Agent Loop Integration

---

## STEP 1: SFT v1 (Baseline Alignment)

**Goal:** Make Qwen follow Claude-style structure reliably.

**Training:**
- Dataset: 503 gold samples ONLY
- Epochs: 1-2 (don't overtrain)
- Base: Qwen2.5-Coder-7B-Instruct

**Expected Output:**
- Correct PLAN/FILES/PATCH/COMMANDS/NOTES structure
- Your coding patterns
- Model v1

**Script:** `train_sft_v1.py`

---

## STEP 2: Evaluation (Critical Gate)

**Goal:** Verify model quality before scaling.

**Test Set:**
- 50-100 unseen prompts
- Real user task types
- Never in training data

**Metrics:**
| Metric | Target |
|--------|--------|
| Format compliance | >95% |
| Code compiles | >85% |
| Tests pass | >70% |
| Security clean | >95% |

**Decision:**
- ❌ Structure inconsistent → Fix dataset
- ❌ Wrong architecture → Add targeted gold samples
- ✅ Mostly correct → Proceed to Step 3

**Script:** `evaluate_v1.py`

---

## STEP 3: Generate Silver Data

**Goal:** Scale dataset using Model v1.

**Process:**
1. Model v1 generates answers for new prompts
2. Auto-check:
   - JSON validity
   - Patch applies cleanly
   - Build/test passes
3. Human review only failures

**Target:** 2k-5k silver samples

**Script:** `generate_silver_data.py`

---

## STEP 4: SFT v2 (Gold + Silver)

**Goal:** Improve coverage across technologies.

**Dataset Composition:**
- 30-40% gold (503 samples)
- 60-70% silver (2k-5k samples)

**Expected Output:**
- Better generalization
- Fewer hallucinations
- Stronger multi-file consistency
- Model v2

**Script:** `train_sft_v2.py`

---

## STEP 5: DPO Training

**Goal:** Teach model to choose best solutions.

**DPO Pair Creation:**
1. Generate 2-4 candidates per prompt
2. Apply patches + run tests
3. chosen = passes tests
4. rejected = fails / insecure

**Target:** 500-2k DPO pairs

**Expected Output:**
- Dramatically increased reliability
- Senior-engineer-like outputs
- Model v3

**Script:** `train_dpo_v3.py`

---

## STEP 6: Agent Loop Integration

**Goal:** Handle failures gracefully.

**Loop:**
```
Generate response
    ↓
Apply patch
    ↓
Run tests
    ↓
If fail → feedback + retry (max 3)
    ↓
Return result
```

**Integration:** `coding_agent.py`

---

## What NOT To Do ❌

- ❌ Don't train on 120k samples immediately
- ❌ Don't do DPO before SFT
- ❌ Don't judge by training loss only
- ❌ Don't skip evaluation

## Practical Numbers

| Stage | Dataset Size |
|-------|--------------|
| SFT v1 | 503 gold |
| SFT v2 | 503 gold + 3k silver |
| DPO | 500-2k pairs |
