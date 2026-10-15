from pathlib import Path
from queue import Full, Queue
from threading import Event, Thread
from time import perf_counter

import cv2


RESOURCE_PATH = Path(__file__).resolve().parent.parent / "resources"
BUFFER_SIZE = 30
PREFILL_FRAMES = 10


def decode_frames(cap, frame_buffer, stop, ready):
    """Read and resize frames in the background."""
    def enqueue(item):
        while not stop.is_set():
            try:
                frame_buffer.put(item, timeout=0.1)
                if frame_buffer.qsize() >= PREFILL_FRAMES:
                    ready.set()
                return
            except Full:
                continue

    error = None
    try:
        while not stop.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(
                frame, None, fx=0.5, fy=0.5,
                interpolation=cv2.INTER_AREA,
            )
            enqueue(frame)
    except Exception as exc:
        error = exc
    finally:
        cap.release()
        # None marks the end; an Exception reports a decoding error.
        enqueue(error)
        ready.set()


def main():
    cap = cv2.VideoCapture(RESOURCE_PATH / "movie.mp4")
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open {RESOURCE_PATH / 'movie.mp4'}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = 1 / fps if fps > 0 else 1 / 30
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps > 0:
        print(f"Video length: {frame_count / fps:.2f} seconds ({fps:g} FPS)")

    output_dir = RESOURCE_PATH / "capture"
    output_dir.mkdir(parents=True, exist_ok=True)
    capture_count = 0

    # Buffer up to 30 frames; start after preparing 10 frames.
    frame_buffer = Queue(maxsize=BUFFER_SIZE)
    stop = Event()
    ready = Event()
    decoder = Thread(
        target=decode_frames,
        args=(cap, frame_buffer, stop, ready),
        name="video-decoder",
    )
    decoder.start()

    try:
        ready.wait()
        next_frame_time = perf_counter()
        quit_requested = False

        while not quit_requested:
            frame = frame_buffer.get()
            if frame is None:
                break
            if isinstance(frame, Exception):
                raise RuntimeError("Video decoding failed") from frame

            # Keep GUI operations on the main thread.
            cv2.imshow("Frame", frame)
            next_frame_time += frame_interval

            while True:
                remaining_ms = (next_frame_time - perf_counter()) * 1000
                key = cv2.waitKey(max(1, round(remaining_ms))) & 0xFF
                if key == ord("q"):
                    quit_requested = True
                    break
                if key == ord("c"):
                    output_path = output_dir / f"capture_{capture_count:04d}.png"
                    if cv2.imwrite(str(output_path), frame):
                        print(f"Saved: {output_path}")
                        capture_count += 1
                if perf_counter() >= next_frame_time:
                    break
    finally:
        stop.set()
        decoder.join()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
