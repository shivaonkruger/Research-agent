
import sys
from agent import graph


def run(question: str, verbose: bool = False):
    print(f"\n{'─'*60}")
    print(f"Question: {question}")
    print(f"{'─'*60}\n")

    initial_state = {"question": question, "search_results": []}

    print("● Searching...")
    print("● Summarizing...")
    print("● Critiquing & generating final response...")

    final_state = graph.invoke(initial_state)

    if verbose:
        print("\n[SEARCH RESULTS]")
        for i, r in enumerate(final_state["search_results"], 1):
            print(f"  {i}. {r['title']} — {r['url']}")

        print("\n[SUMMARY]")
        print(final_state["summary"])

        print("\n[CRITIQUE]")
        print(final_state["critique"])

    print("\n[FINAL RESPONSE]")
    print(final_state["final_response"])
    print(f"\n{'─'*60}\n")


def main():
    verbose = "--verbose" in sys.argv

    print("╔══════════════════════════════════════════════╗")
    print("║     Research Workflow  (Cerebras + Tavily)   ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  --verbose  →  show search results + summary ║")
    print("║  quit/exit  →  exit                          ║")
    print("╚══════════════════════════════════════════════╝\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit"):
            print("Exiting.")
            break

        try:
            run(question, verbose=verbose)
        except Exception as e:
            print(f"[Error] {e}")


if __name__ == "__main__":
    main()