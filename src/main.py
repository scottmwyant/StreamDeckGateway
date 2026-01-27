import time
from driver import Driver


def run():

    driver = Driver()
    print(driver.deviceInfo)
    return 

    driver.start()

    try:
        while True:
            # Get events from the driver
            newState = driver.msgQ.get(block=False)
            print(f"newState: {newState}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping...")

# def run():
#     """This is is where we orchestrate the producer/consumer pattern."""
    
#     # Use a set of Queue objects to interact with a
#     # background thread that owns HID communication.
#     # msgqTx = messages to the HID thread
#     # msgqRx = messages from the HID thread 
    # msgqRx, msgqTx = (Queue(), Queue())
    

#     thread = threading.Thread(target=producer, args=(q,), daemon=True, name="Driver")
#     thread.start()
#     doMainLoop(q)

    
# def doMainLoop(queue: Queue):
    
#     # Main thread: consume messages
#     try:
#         while True:
#             message = queue.get(timeout=2)
#             if message is not None:
#                 print("Message received")
#                 time.sleep(1)

#     except KeyboardInterrupt:
#         print("Shutting down...")


# def producer(queue: Queue):
#     """This function runs on a background thread, producing messages."""
#     print(f"[{threading.current_thread().name}] started")
#     while True:
#         print(f"[{threading.current_thread().name}] Message going into queue")
#         queue.put("Message produced")
#         time.sleep(2)




if __name__ == "__main__":
    run()