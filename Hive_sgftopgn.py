import re
from collections import defaultdict
import sys


def main():
    filename = sys.argv[1][:-4]
    expansions = {"M": 0, "L": 0, "P": 0}
    with open(f"{filename}.sgf", "r") as file_read:
        lines = file_read.readlines()
    write_header(lines[:10], filename, expansions)
    append_moves(lines[10:], filename, expansions)


def write_header(sgf_head, filename, expansions):
    pattern_gametype = r"^SU\[(.*)\]$"
    pattern_result = r"RE\[(?:Game won by )?(?:The game is a )?(.*)\]$"
    pattern_white = r"P0\[id \"(.*)\"\]$"
    pattern_black = r"P1\[id \"(.*)\"\]$"
    exp_pieces = gametype = white = black = result = ""
    date = '[Date ""]'
    event = '[Event ""]'
    site = '[Site ""]'
    round = '[Round ""]'
    players = {}
    for line in sgf_head:
        if not gametype:
            match = re.search(pattern_gametype, line)
            if match:
                gametype = match.group(1)
                continue
        if not result:
            match = re.search(pattern_result, line)
            if match:
                result = match.group(1)
                continue

        if not white:
            match = re.search(pattern_white, line)
            if match:
                players[match.group(1)] = "White"
                white = f'[White "{match.group(1)}"]'
                continue
        if not black:
            match = re.search(pattern_black, line)
            if match:
                players[match.group(1)] = "Black"
                black = f'[Black "{match.group(1)}"]'
                break
    if result == "draw":
        last_line = result.title()
        result = f"[Result {last_line}]"
    else:
        last_line = f'"{players[result]}Wins"'
        result = f"[Result {last_line}]"
    if len(gametype) == 4:
        gametype = '[GameType "Base"]'
    else:
        for char in gametype[-3:]:
            if char in expansions:
                expansions[char] += 1

        for k, v in expansions.items():
            if v:
                exp_pieces += k
        gametype = f'[GameType "Base+{exp_pieces}"]'

    with open(f"{filename}.pgn", "w") as file_write:
        file_write.write(
            f"{gametype}\n{date}\n{event}\n{site}\n{round}\n{white}\n{black}\n{result}\n\n"
        )


def append_moves(sgf_body, filename, expansions):
    pattern_player = r".*ropb([A-Za-z0-9 \\\/-]+\.?).*\]$"
    pattern_pass = r".*([Pp]ass).*$"
    pattern_move = r".*[Mm]ove [BW] ([A-Za-z0-9 \\\/-]+\.?).*\]$"
    matches = [
        match.group(1)
        for string in sgf_body
        for pattern in (pattern_move, pattern_pass, pattern_player)
        for match in re.finditer(pattern, string)
        if match
    ]
    i = 1
    lookup_table = defaultdict(list)
    reverse_lookup = {}

    with open(f"{filename}.pgn", "a") as file_write:
        for line in matches:
            line = line.strip()
            if line != "Pass" and line != "pass":
                turn = line.split()
                placed_bug = turn[0]

                # strip extra number for l/m/p
                if placed_bug[1] in expansions:
                    placed_bug = placed_bug[:-1]

                # no need to escape \ in pgn
                destination = re.sub(r"\\\\", r"\\", turn[-1])

                coordinates = "-".join(turn[1:-1])

                # . on bs is used for the first move where it won't reference another piece and for moves on top of the hive
                if destination == ".":
                    if i == 1:
                        destination = ""
                    else:
                        # for moves on top of the hive bs uses it's coordinate system instead of referencing another piece as usual
                        try:
                            destination = lookup_table[coordinates][-1]
                        except IndexError:
                            current_x, current_y = reverse_lookup[placed_bug].split("-")
                            destination_x, destination_y = coordinates.split("-")
                            print(current_x, current_y, destination_x, destination_y)
                            destination = handle_unvisited_hex(
                                current_x,
                                int(current_y),
                                destination_x,
                                int(destination_y),
                                placed_bug,
                            )
                if placed_bug in reverse_lookup:
                    lookup_table[reverse_lookup[placed_bug]].pop()
                reverse_lookup[placed_bug] = coordinates
                lookup_table[coordinates].append(placed_bug)
            else:
                placed_bug = "pass"
                destination = ""
            file_write.write(f"{i}. {placed_bug} {destination}\n")
            i += 1


def handle_unvisited_hex(
    current_x, current_y, destination_x, destination_y, placed_bug
):
    if current_y == destination_y:
        if ord(current_x) > ord(destination_x):
            return f"-{placed_bug}"
        else:
            return f"{placed_bug}-"
    if current_x == destination_x:
        if current_y > destination_y:
            return f"\\{placed_bug}"
        else:
            return f"{placed_bug}\\"
    if current_y > destination_y:
        return f"{placed_bug}/"
    return f"/{placed_bug}"


if __name__ == "__main__":
    main()
