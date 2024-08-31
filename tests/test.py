async def main():
    import os
    os.environ["OPENAI_API_KEY"] = ""
    stages = [
        Stage(name="Example Stage", description="This is an example stage", query="hello"),
        Stage(name="Another Example Stage", description="This is another example stage", query="when is chrismas?"),
        Stage(name="Final Stage", description="This is the final stage", query="can it be moved?")
    ]

    worker = Worker(stages)

    r = await worker.exhaust_stages()
    print("history:", worker.history)
    print("Result:", r)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
