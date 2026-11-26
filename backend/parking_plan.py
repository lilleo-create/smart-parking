from collections import defaultdict
from statistics import mean, median


def axis_tracks(spots, axis):
    edges = [(spot["bounds"][axis], spot["bounds"][axis + 2]) for spot in spots]
    centers = [(start + end) / 2 for start, end in edges]
    typical_size = median(end - start for start, end in edges)

    # Limit each cluster's full span so small offsets cannot chain whole rows together.
    groups = []
    for index in sorted(range(len(spots)), key=centers.__getitem__):
        if not groups or centers[index] - centers[groups[-1][0]] > typical_size * 0.6:
            groups.append([])
        groups[-1].append(index)

    anchors = [mean(centers[index] for index in group) for group in groups]
    gaps = [right - left for left, right in zip(anchors, anchors[1:])]
    neighboring_gaps = [gap for gap in gaps if gap <= typical_size * 1.8]
    pitch = max(typical_size, median(neighboring_gaps)) if neighboring_gaps else typical_size

    tracks = [0] * len(spots)
    track = 1
    for gap, group in zip([0] + gaps, groups):
        if gap > pitch * 1.8:
            track += 1  # Keep a visible aisle without scaling the entire plan to the frame.
        for index in group:
            tracks[index] = track
        track += 1
    return tracks


def spatial_plan(spots):
    columns = axis_tracks(spots, 0)
    rows = axis_tracks(spots, 1)
    cells = defaultdict(list)
    for row, column, spot in zip(rows, columns, spots):
        cells[row, column].append(spot)

    # Draw every ID even if two overlapping rectangles snap to the same cell.
    widths = defaultdict(lambda: 1)
    for (_, column), cell in cells.items():
        widths[column] = max(widths[column], len(cell))
    starts = {}
    start = 1
    for column in range(1, max(columns) + 1):
        starts[column] = start
        start += widths[column]

    plan = []
    for (row, column), cell in sorted(cells.items()):
        ordered = sorted(cell, key=lambda spot: (spot["bounds"][0] + spot["bounds"][2], spot["id"]))
        for offset, spot in enumerate(ordered):
            plan.append({
                "id": spot["id"], "label": str(spot["number"]),
                "row": str(row), "planRow": row, "position": starts[column] + offset,
            })
    return plan
