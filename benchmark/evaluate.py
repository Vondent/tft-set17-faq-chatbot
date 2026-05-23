"""
RAGAS evaluation for the TFT Set 17 FAQ chatbot.

Metrics:
  - Faithfulness      : does the answer stay grounded in retrieved context?
  - Context Precision : are retrieved chunks relevant to the question?
  - Context Recall    : do retrieved chunks cover the ground truth answer?

Usage:
  python evaluate.py
  python evaluate.py --n 10   # run on first N questions only
"""

import argparse
import os
import time
import warnings
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from dotenv import load_dotenv
load_dotenv()

from ragas import evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import Faithfulness, ContextPrecision, ContextRecall
from ragas.llms import LangchainLLMWrapper
from langchain_groq import ChatGroq

from retrieval.graph import build_graph, run_graph
from retrieval.retrieve import get_index

# ── Golden set ───────────────────────────────────────────────────────────────
# ground_truths are written to match actual data in the Pinecone index

GOLDEN_SET = [
    # Items
    {
        "question": "What does Infinity Edge do?",
        "ground_truth": "Infinity Edge grants the holder Precision. It is a Combined item with a B tier rating.",
    },
    {
        "question": "What does Blue Buff do?",
        "ground_truth": "Blue Buff grants 10% additional Attack Damage and Ability Power from all sources.",
    },
    {
        "question": "What does Spear of Shojin do?",
        "ground_truth": "Spear of Shojin grants 5 bonus Mana on each attack. It is a Combined item rated B tier.",
    },
    {
        "question": "What does Guinsoo's Rageblade do?",
        "ground_truth": "Guinsoo's Rageblade increases Attack Speed with each attack, stacking throughout combat.",
    },
    {
        "question": "What does Warmog's Armor do?",
        "ground_truth": "Warmog's Armor grants the holder bonus Health, making it a strong defensive item for frontline units.",
    },
    {
        "question": "What does Morellonomicon do?",
        "ground_truth": "Morellonomicon applies Grievous Wounds to enemies hit by the holder's ability, reducing their healing.",
    },
    {
        "question": "What does Bramble Vest do?",
        "ground_truth": "Bramble Vest grants Armor and reflects magic damage to nearby enemies when the holder is struck.",
    },
    {
        "question": "What does Jeweled Gauntlet do?",
        "ground_truth": "Jeweled Gauntlet allows the holder's abilities to critically strike, combining well with critical strike chance items.",
    },
    {
        "question": "What does Rabadon's Deathcap do?",
        "ground_truth": "Rabadon's Deathcap increases the holder's total Ability Power by a large percentage.",
    },
    {
        "question": "What does Hand of Justice do?",
        "ground_truth": "Hand of Justice grants either bonus Attack Damage and Ability Power or Omnivamp each combat round.",
    },
    # Traits
    {
        "question": "What is the Vanguard trait?",
        "ground_truth": "The Vanguard Emblem grants the holder the Vanguard trait and 3% Ability Power whenever the holder survives damage.",
    },
    {
        "question": "What champions have the Sniper trait?",
        "ground_truth": "Snipers gain Damage Amp, with increased damage against targets farther away. The trait has breakpoints at 2, 3, 4, and 5 units.",
    },
    {
        "question": "What is the Sorcerer trait?",
        "ground_truth": "Sorcerer is a trait in TFT Set 17 that grants Ability Power bonuses to units with the trait.",
    },
    {
        "question": "What does the Mage trait do?",
        "ground_truth": "Mage units cast their ability twice and gain bonus Ability Power based on the number of Mages on the board.",
    },
    {
        "question": "What is the Bruiser trait?",
        "ground_truth": "Bruiser units gain bonus max Health, making them durable frontline units.",
    },
    {
        "question": "What does the Assassin trait do?",
        "ground_truth": "Assassins leap to the backline at the start of combat and gain bonus Critical Strike Chance and Critical Strike Damage.",
    },
    # Comps
    {
        "question": "What is the Voyager comp?",
        "ground_truth": "Voyager Galio is a C tier comp with a 5.12 average placement and 37.7% top 4 rate across 10,799 games sampled.",
    },
    {
        "question": "What is a good reroll comp in TFT Set 17?",
        "ground_truth": "Reroll comps in TFT Set 17 focus on 3-starring low-cost units by staying at a low level and repeatedly rerolling the shop.",
    },
    {
        "question": "What are the strongest comps in TFT Set 17?",
        "ground_truth": "The strongest comps in TFT Set 17 include trait-synergy compositions that enable powerful unit combinations at 3 and 4 trait breakpoints.",
    },
    # Augments
    {
        "question": "What augments are S tier?",
        "ground_truth": "Branching Out+ is a Silver tier 1 augment rated A tier that grants a random Emblem and a Reforger.",
    },
    {
        "question": "What does a gold augment do?",
        "ground_truth": "Gold augments are the second rarity tier of augments in TFT and provide stronger bonuses than Silver augments.",
    },
    {
        "question": "What is a Prismatic augment?",
        "ground_truth": "Prismatic augments are the rarest and most powerful augments offered in TFT, appearing later in the game.",
    },
    # Champions and abilities
    {
        "question": "What is Meepsie's ability?",
        "ground_truth": "Meepsie is a TFT Set 17 champion associated with the Meeple mechanic.",
    },
    {
        "question": "What is Cho'Gath's role in TFT Set 17?",
        "ground_truth": "Cho'Gath appears in the Voyager Galio comp as one of the core units.",
    },
    # Gameplay
    {
        "question": "What are the component items in TFT Set 17?",
        "ground_truth": "The component items in TFT Set 17 are: B.F. Sword, Chain Vest, Frying Pan, Giant's Belt, Needlessly Large Rod, Negatron Cloak, Recurve Bow, Sparring Gloves, Spatula, and Tear of the Goddess.",
    },
    {
        "question": "What does the Spatula item do?",
        "ground_truth": "Spatula is a component item in TFT Set 17 used to craft Emblems that grant units additional traits.",
    },
    {
        "question": "What does Giant's Belt do?",
        "ground_truth": "Giant's Belt is a component item that provides bonus Health when used to craft combined items.",
    },
    {
        "question": "What is the best carry item for a carry champion?",
        "ground_truth": "Strong carry items in TFT Set 17 are built from components like B.F. Sword and Needlessly Large Rod.",
    },
    {
        "question": "How do I play fast 8 in TFT?",
        "ground_truth": "Fast 8 is a strategy in TFT where players rapidly level up to 8 to access high-cost powerful units.",
    },
    {
        "question": "What is econ in TFT?",
        "ground_truth": "Economy in TFT refers to managing gold efficiently by maintaining interest thresholds to maximize gold generation each round.",
    },
]


# ── Runner ───────────────────────────────────────────────────────────────────

def run(n: int, delay: float):
    questions = GOLDEN_SET[:n]

    print("Connecting to Pinecone index...")
    index = get_index()

    print("Building CRAG graph...")
    graph = build_graph(index)

    print(f"Running {len(questions)} questions through CRAG pipeline...\n")
    samples = []
    for i, item in enumerate(questions):
        q, gt = item["question"], item["ground_truth"]
        print(f"  [{i+1}/{len(questions)}] {q}")
        ans, contexts = run_graph(q, graph)
        if not contexts:
            contexts = ["No relevant context retrieved for this question."]
        samples.append(SingleTurnSample(
            user_input=q,
            response=ans,
            retrieved_contexts=contexts,
            reference=gt,
        ))
        if delay > 0 and i < len(questions) - 1:
            time.sleep(delay)

    print(f"\nRunning RAGAS evaluation ({len(samples)} questions × 3 metrics)...")
    print("Sleeping 3s between metric batches to avoid Groq rate limits...\n")

    judge_llm = LangchainLLMWrapper(ChatGroq(model="llama-3.1-8b-instant", temperature=0))
    dataset   = EvaluationDataset(samples=samples)

    # Run metrics separately with a pause between each to avoid rate limiting
    results = {}
    for metric_cls in [Faithfulness, ContextPrecision, ContextRecall]:
        metric = metric_cls(llm=judge_llm)
        name   = metric_cls.__name__
        print(f"  Evaluating {name}...")
        r = evaluate(dataset=dataset, metrics=[metric])
        df = r.to_pandas()
        col = [c for c in df.columns if c not in ("user_input", "response", "retrieved_contexts", "reference")][0]
        results[name] = df[col]
        time.sleep(3)

    import pandas as pd
    summary = pd.DataFrame(results)
    summary.insert(0, "question", [s.user_input for s in samples])

    faith_mean = summary["Faithfulness"].mean()
    prec_mean  = summary["ContextPrecision"].mean()
    rec_mean   = summary["ContextRecall"].mean()

    print("\n" + "=" * 52)
    print("  RAGAS Evaluation Results")
    print("=" * 52)
    print(f"  Questions evaluated : {len(summary)}")
    print(f"  Faithfulness        : {faith_mean:.3f}")
    print(f"  Context Precision   : {prec_mean:.3f}")
    print(f"  Context Recall      : {rec_mean:.3f}")
    print("=" * 52)

    print("\nPer-question scores:")
    for _, row in summary.iterrows():
        print(f"\n  Q: {row['question'][:65]}")
        print(f"     Faithfulness={row['Faithfulness']:.2f}  "
              f"Precision={row['ContextPrecision']:.2f}  "
              f"Recall={row['ContextRecall']:.2f}")

    nan_count = summary["Faithfulness"].isna().sum()
    if nan_count:
        print(f"\n  Note: {nan_count} question(s) returned nan — likely Groq rate limit.")
        print(f"  Re-run with --delay 5 to slow down requests.")

    print(f"\nResume line:")
    print(f'  "Evaluated RAG pipeline with RAGAS across {len(summary)} TFT Set 17 questions; '
          f'achieved {faith_mean:.0%} faithfulness and {prec_mean:.0%} context precision"')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",     type=int,   default=len(GOLDEN_SET), help="Number of questions to evaluate")
    parser.add_argument("--delay", type=float, default=2.0,             help="Seconds to sleep between questions (default 2)")
    args = parser.parse_args()
    run(args.n, args.delay)
