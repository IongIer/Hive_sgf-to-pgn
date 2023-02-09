import re
import os
import glob
from collections import defaultdict


def main():
    filenames = [filename[:-4] for filename in glob.glob("./*.sgf")]
    dir_path = "./pgn/"
    os.makedirs(dir_path, exist_ok=True)
    for filename in filenames:
        make_pgn(filename, dir_path)


def make_pgn(filename, dir_path):
    expansions = {"M": 0, "L": 0, "P": 0}
    with open(f"{filename}.sgf", "r") as file_read:
        lines = file_read.readlines()
    write_header(lines[:10], filename, expansions, lines[-7], dir_path)
    append_moves(lines[10:], filename, expansions, dir_path)


def write_header(sgf_head, filename, expansions, sgf_tail, dir_path):

    # regex that will handle result in games where resign or accept draw took place, this helps because it's more reliable than the result line in the sgf in some cases
    pattern_end = r"^; (P\d)\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$"

    # the first part of the sgf is predictible so string slices are used to extract the info instead of regex

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

    # try to see if the game finished by agreement
    match = re.match(pattern_end, sgf_tail)
    if match:
        player = match.group(1)
        outcome = match.group(2)
        if outcome.lower() != "resign":
            res = "1/2-1/2"
        else:
            if player == "P0":
                res = "0-1"
            else:
                res = "1-0"

    # extract result from result line
    if not res:
        res = sgf_head[7].split(" ")[-1][:-2]
        if res == "draw":
            res = "1/2-1/2"
        else:
            try:
                res = f"{players[res]}"

            # this will sometimes happen due to how boardspace saves results for guest games and games where the player who won was using a localized language version
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

    with open(os.path.join(dir_path, f"{filename}.pgn"), "w") as file_write:
        file_write.write(
            f"{gametype}\n{date}\n{event}\n{site}\n{round}\n{white}\n{black}\n{result}\n\n"
        )


def append_moves(sgf_body, filename, expansions, dir_path):

    end = r"(:?[Aa]ccept[dD]raw)|(:?[rR]esign)"
    i = 1
    lookup_table = defaultdict(list)
    reverse_lookup = {}
    placed_bug = ""
    destination = ""
    coordinates = ""
    draw = False

    with open(os.path.join(dir_path, f"{filename}.pgn"), "a") as file_write:
        for unprocessed_line in sgf_body:
            line = match_line(unprocessed_line)
            if not line:
                continue
            # stop writing in case a resign or accept draw is encountered
            if re.match(end, line):
                return
            line = line.strip()
            low = line.lower()
            # for draw offers and refusals, the next done needs to be skipped
            if low == "draw":
                draw = True
                continue
            # write the next line to a file when a done is encountered but only if it wasn't part of a draw offer or refusal
            if low == "done":
                if draw:
                    draw = False
                    continue
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
            # update the current move to be written
            elif low != "pass":
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
                            destination = drop_down_bug(
                                current_x,
                                int(current_y),
                                destination_x,
                                int(destination_y),
                                placed_bug,
                            )
            # in case a player can't move
            else:
                placed_bug = "pass"
                destination = ""


def match_line(line):
    patterns = [
        r".*ropb([A-Za-z0-9 \\\/-]+\.?).*\]$",
        r".*([Pp]ass).*$",
        r".*[Mm]ove [BW] ([A-Za-z0-9 \\\/-]+\.?).*\]$",
        r"^; P[01]\[\d+ ([dD]one).*$",
        r"^; P\d\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$",
        r"^; P\d\[\d+ (?:[Dd]ecline)?(?:[Oo]ffer)?([Dd]raw)+.*$",
    ]
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            return match.group(1)
    return ""


# six different cases depending on current coordinates and destination coordinates
def drop_down_bug(current_x, current_y, destination_x, destination_y, placed_bug):
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
