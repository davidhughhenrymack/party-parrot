import linecache
import tracemalloc


def display_top(snapshot, key_type="lineno", limit=10):
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("\033[94m---- Top %s lines ----\033[0m" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print(
            "\033[94m#%s: %s:%s: %.1f KiB\033[0m"
            % (index, frame.filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    \033[94m%s\033[0m" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("\033[92m%s other: %.1f KiB\033[0m" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("\033[92mTotal allocated size: %.1f KiB\033[0m" % (total / 1024))
