import re
from collections import defaultdict
import sys


def main():
    filename = sys.argv[1][:-4]
    expansions = {"M": 0, "L": 0, "P": 0}
    with open(f"{filename}.sgf", "r") as file_read:
        lines = file_read.readlines()
    write_header(lines[:10], filename, expansions, lines[-7])
    append_moves(lines[10:], filename, expansions)


def write_header(sgf_head, filename, expansions, sgf_tail):

    pattern_end = r"^; (P\d)\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$"
    extracted_date = ".".join(filename.split("-")[-4:-1])
    extracted_white = sgf_head[8].split(" ")[-1][:-2].strip('"')
    extracted_black = sgf_head[9].split(" ")[-1][:-2].strip('"')
    res = ""
    date = f'[Date "{extracted_date}"]'
    event = f'[Event ""]'
    site = f'[Site "boardspace.net"]'
    round = f'[Round ""]'
    white = f'[White "{extracted_white}"]'
    black = f'[Black "{extracted_black}"]'
    players = {extracted_white: "1-0", extracted_black: "0-1"}
    match = re.match(pattern_end, sgf_tail)
    if match:
        player = match.group(1)
        outcome = match.group(2)
        if outcome != "resign" and outcome != "Resign":
            res = "1/2-1/2"
        else:
            if player == "P0":
                res = "0-1"
            else:
                res = "1-0"

    if not res:
        res = sgf_head[7].split(" ")[-1][:-2]
        if res == "draw":
            res = "1/2-1/2"
        else:
            try:
                res = f"{players[res]}"
            except KeyError:
                res = "error parsing result"

    result = f'[Result "{res}"]'

    gametype = sgf_head[4][3:-2]
    if gametype == "Hive-Ultimate":
        print("Hive-Ultimate not supported")
        sys.exit(1)
    exp_pieces = ""

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
    pattern_done = r"^; P[01]\[\d+ ([dD]one).*$"
    pattern_end = r"^; P\d\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$"
    end = r"(:?[Aa]ccept[dD]raw)|(:?[rR]esign)"
    matches = [
        match.group(1)
        for string in sgf_body
        for pattern in (
            pattern_move,
            pattern_pass,
            pattern_player,
            pattern_done,
            pattern_end,
        )
        for match in re.finditer(pattern, string)
        if match
    ]
    i = 1
    lookup_table = defaultdict(list)
    reverse_lookup = {}
    placed_bug = ""
    destination = ""
    coordinates = ""

    with open(f"{filename}.pgn", "a") as file_write:
        for line in matches:
            if re.match(end, line):
                return

            line = line.strip()
            if line == "Done" or line == "done":
                if not placed_bug:
                    placed_bug = "pass"
                    destination = ""

                file_write.write(f"{i}. {placed_bug} {destination}\n")
                if placed_bug in reverse_lookup:
                    lookup_table[reverse_lookup[placed_bug]].pop()
                reverse_lookup[placed_bug] = coordinates
                lookup_table[coordinates].append(placed_bug)
                i += 1
                placed_bug = ""
                destination = ""
                coordinates = ""
            elif line != "Pass" and line != "pass":
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

                        # when dropping down the same . is used but the above will fail because there is no piece there
                        except IndexError:
                            current_x, current_y = reverse_lookup[placed_bug].split("-")
                            destination_x, destination_y = coordinates.split("-")
                            destination = handle_unvisited_hex(
                                current_x,
                                int(current_y),
                                destination_x,
                                int(destination_y),
                                placed_bug,
                            )

            else:
                placed_bug = "pass"
                destination = ""


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
            return f"{placed_bug}\\"
        else:
            return f"\\{placed_bug}"
    if current_y > destination_y:
        return f"/{placed_bug}"
    return f"{placed_bug}/"


if __name__ == "__main__":
    main()
