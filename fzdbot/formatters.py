# This file contains format functions for displaying results from past events into discord,
# mainly used in the "/show" command as of right now
from datetime import datetime, timedelta, timezone

def format_discord_timestamp(dt, inline=False) -> str:
    """ Flexible timestamp builder.
        If the event is not in the next few hours, it will use
        a different format automatically.
        Set inline to True if the timestamp appears in a
        started sentence.
    """
    delta = dt - datetime.now(timezone.utc)
    t_format = 'f'
    if inline:
       particle = 'on '
    else:
       particle = ''
    text = "{0}<t:{1}:{2}>"
    return text.format(particle, int(dt.timestamp()), t_format)

def format_scoreboard_display_text(allscores) -> list[str]:
    """  Takes as input the list of dictionaries with players and scores from sql, 
         calculates rank (assuming the input is ordered already by max score)
         and outputs a list of text lines for each player, 
         where each line contains rank, player name, and scores
         (with some other formatting/flair for a nice-looking scoreboard display)
    """
    qualemoji="<:LuckyRank:1213541741450231878>"
    scoreboard=[]    
    if "is_qualified" in allscores[0] and any(d.get("is_qualified") == 1 for d in allscores):
       scoreboard.append(f"*{qualemoji} = already qualified for Team World*\n")

    #teamDisplay = False
    #if "team" in allscores[0] and any(d.get("team") is not None for d in allscores):
    #   teamDisplay = True
    
    #if teamDisplay:
    isBelowPodium = False
    team_names = {d['team'] for d in allscores}
    team_names.discard(None) # Remove any non-team entries
    if team_names: 
        print(team_names)
        team_scores=[]
        for team in team_names: 
            team_scores.append((sum([s['score'] for s in allscores if s['team'] == team]),team))
        print(team_scores)
        
        #team_scores_and_names = zip(team_scores, team_names)
        sorted_team_results = sorted(team_scores, reverse=True)
        print(sorted_team_results)  
      
        rank=0
        last_score = None
        #isBelowPodium = False
        for iscore, (score, team) in enumerate(sorted_team_results):
            if score != last_score:
                rank = iscore + 1
            
            rankdisplay=" "+str(rank)+"\\."
            if rank == 1:
                rankdisplay="<:1st:1201576405339754546> " #emoji=":trophy: "
            elif rank == 2:
                rankdisplay="<:2nd:1201576409638903858> " #":second_place: "
            elif rank == 3:
                rankdisplay="<:3rd:1201576412444905653> " #":third_place: "
            
            if not isBelowPodium and rank > 3:
               # scoreboard.append("======================")
                isBelowPodium = True

            # If we don't escape the dot ("\\.") discord might see the rank as markdown text 
            # And weird behavior could happen as a result
            scoreboard.append(f"**{rankdisplay} {team} - {score}**")
            last_score = score
        scoreboard.append("\n INDIVIDUAL RESULTS:")
    
    rank=0
    last_score = None 
    #isBelowPodium = False
    for iscore, entry in enumerate(allscores):
        player = entry['player']
        score = int(entry['score'])
        if score != last_score:
            rank = iscore + 1

        rankdisplay=str(rank)+"\\."
        if rank == 1:
            rankdisplay="<:1st:1201576405339754546> " #emoji=":trophy: "
        elif rank == 2:
            rankdisplay="<:2nd:1201576409638903858> " #":second_place: "
        elif rank == 3:
            rankdisplay="<:3rd:1201576412444905653> " #":third_place: "
        
        if team_names:
            rankdisplay=f"{entry['team']}: "      
 
        qualdisplay=""
        if "is_qualified" in entry and entry["is_qualified"] == 1:
            qualdisplay=f"{qualemoji} "

        if not isBelowPodium and rank > 3:
            scoreboard.append("======================")
            isBelowPodium = True
        
        # If we don't escape the dot ("\\.") discord might see the rank as markdown text 
        # And weird behavior could happen as a result
        scoreboard.append(f"{rankdisplay}{qualdisplay} **{player}** - {score}")
        last_score = score
    #print(sum(len(s) for s in scoreboard)) 
    return scoreboard

def format_scoreboard_for_discord_embed(lines: list[str], 
                                 max_num_lines: int = 100,
                             max_field_length: int = 1024) -> list[str]:
    """
    Given a list of lines, split them into blocks that fit into Discord embed fields.
    max_num_lines:  optional max number of lines to display on the scoreboard
    max_field_length: Each field has a max length of 1024 in discord (keep as is unless discord changes it) 
    """

    curstr = ""
    formatted_fields = []
    linecount: int = 0
    maxlines: int = max_num_lines + 1 # Accounts for added line of "=" in formatting of podium
    for line in lines:
        if (len(curstr) + len(line) + 1 > max_field_length or linecount >= maxlines ):               
            formatted_fields.append(curstr)
            curstr = ""
            linecount = 0
            maxlines = max_num_lines 

        curstr += line + "\n"
        linecount += 1

    # Don’t forget the last block
    if curstr:
        formatted_fields.append(curstr)
   
    #print(sum(len(s) for s in formatted_fields)) 
    return formatted_fields  
