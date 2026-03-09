def deduplicate_tasks(signals: list[Signal]) -> list[UnifiedTask]:
    grouped: dict[str, list[Signal]] = {}
    for signal in signals:
        grouped.setdefault(_group_key(signal), []).append(signal)

    tasks: list[UnifiedTask] = []
    for group, items in grouped.items():
        title = items[0].title
        description_parts = []
        owners = {s.owner for s in items if s.owner}
        sources = {s.source for s in items}
        ids = []

        for item in items:
            snippet = item.body.strip()
            if snippet:
                description_parts.append(f"[{item.source.value}] {snippet}")
            ids.append(item.id)

        tasks.append(
            UnifiedTask(
                id=group,
                title=title,
                description="\n".join(description_parts),
                owners=sorted(owners),
                sources=sorted(sources, key=lambda s: s.value),
                linked_signal_ids=ids,
            )
        )

    return tasks