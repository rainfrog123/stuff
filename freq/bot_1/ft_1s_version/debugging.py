import asyncio

async def my_coroutine():
    print("Start")
    await asyncio.sleep(2)  # Simulate a non-blocking operation
    print("End")

async def main():
    task = asyncio.create_task(my_coroutine())
    await task

if __name__ == "__main__":
    asyncio.run(main())
