
import asyncio

from langchain_core.messages import HumanMessage

from backend.graph import build_graph


async def main():

    print("Initializing RepoGuide Agent...")

    graph = await build_graph()

    print("Agent initialized successfully!")

    print("\nAsk a question about the repository.")
    print("Type 'exit' to stop.\n")

    while True:

        question = input("You: ").strip()

        if question.lower() in ["exit", "quit"]:
            break

        if not question:
            continue

        try:

            result = await graph.ainvoke(
                {
                    "messages": [
                        HumanMessage(content=question)
                    ]
                },
                config={
                    "recursion_limit": 10
                }
            )

            response = result["messages"][-1]

            print("\nRepoGuide:")
            print(response.content)
            print("\n" + "-" * 60)

        except Exception as error:

            print("\nError:", error)


if __name__ == "__main__":
    asyncio.run(main())
