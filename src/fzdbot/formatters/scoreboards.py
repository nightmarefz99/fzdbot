def format_scoreboard_display_text(allscores) -> list[str]:
    """Format scoreboard rows for Discord display."""
    qualemoji = "<:LuckyRank:1213541741450231878>"
    scoreboard = []
    if "is_qualified" in allscores[0] and any(item.get("is_qualified") == 1 for item in allscores):
        scoreboard.append(f"*{qualemoji} = already qualified for Team World*\n")

    is_below_podium = False
    team_names = {item["team"] for item in allscores}
    team_names.discard(None)
    if team_names:
        team_scores = []
        for team in team_names:
            team_scores.append((sum(score["score"] for score in allscores if score["team"] == team), team))

        sorted_team_results = sorted(team_scores, reverse=True)
        rank = 0
        last_score = None
        for index, (score, team) in enumerate(sorted_team_results, start=1):
            if score != last_score:
                rank = index

            rankdisplay = f" {rank}\\."
            if rank == 1:
                rankdisplay = "<:1st:1201576405339754546> "
            elif rank == 2:
                rankdisplay = "<:2nd:1201576409638903858> "
            elif rank == 3:
                rankdisplay = "<:3rd:1201576412444905653> "

            if not is_below_podium and rank > 3:
                is_below_podium = True

            scoreboard.append(f"**{rankdisplay} {team} - {score}**")
            last_score = score
        scoreboard.append("\n INDIVIDUAL RESULTS:")

    rank = 0
    last_score = None
    for index, entry in enumerate(allscores, start=1):
        player = entry["player"]
        score = int(entry["score"])
        if score != last_score:
            rank = index

        rankdisplay = f"{rank}\\."
        if rank == 1:
            rankdisplay = "<:1st:1201576405339754546> "
        elif rank == 2:
            rankdisplay = "<:2nd:1201576409638903858> "
        elif rank == 3:
            rankdisplay = "<:3rd:1201576412444905653> "

        if team_names:
            rankdisplay = f"{entry['team']}: "
            if "emote" in entry:
                rankdisplay = f"{entry['emote']} "

        qualdisplay = ""
        if "is_qualified" in entry and entry["is_qualified"] == 1:
            qualdisplay = f"{qualemoji} "

        if not team_names and not is_below_podium and rank > 3:
            scoreboard.append("======================")
            is_below_podium = True

        scoreboard.append(f"{rankdisplay}{qualdisplay} **{player}** - {score}")
        last_score = score

    return scoreboard


def format_scoreboard_for_discord_embed(lines: list[str], max_num_lines: int = 100, max_field_length: int = 1024) -> list[str]:
    """Split scoreboard lines into embed-sized blocks."""
    curstr = ""
    formatted_fields = []
    linecount = 0
    maxlines = max_num_lines + 1
    for line in lines:
        if len(curstr) + len(line) + 1 > max_field_length or linecount >= maxlines:
            formatted_fields.append(curstr)
            curstr = ""
            linecount = 0
            maxlines = max_num_lines

        curstr += line + "\n"
        linecount += 1

    if curstr:
        formatted_fields.append(curstr)

    return formatted_fields
