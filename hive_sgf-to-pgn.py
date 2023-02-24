#!/usr/bin/env python3
import re
import os
import glob
import argparse
from collections import deque
from functools import partial
from collections import defaultdict
from multiprocessing import Pool


def main():
    parsed_args = parse_arguments()
    sgf_folder = os.path.normpath(vars(parsed_args)["path"])
    pgn_path = os.path.normpath(f"{sgf_folder}//pgn//")
    os.makedirs(pgn_path, exist_ok=True)
    make_pgn_at = partial(make_pgn, sgf_path=sgf_folder)
    filenames = [
        os.path.basename(filename)[:-4]
        for filename in glob.glob(f"{sgf_folder}//*.sgf")
    ]
    with Pool() as p:
        p.map(make_pgn_at, filenames)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Command line tool to convert boardspace hive sgf files to pgn"
    )
    parser.add_argument("-path", type=dir_path, required=True)

    return parser.parse_args()


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory")


def make_pgn(filename, sgf_path):
    expansions = {"M": 0, "L": 0, "P": 0}
    with open(
        os.path.join(sgf_path, f"{filename}.sgf"), "r", encoding="utf-8"
    ) as file_read:
        lines = deque(file_read.readlines())
    write_header(lines, filename, expansions, lines[-7], sgf_path)


def write_header(lines, filename, expansions, sgf_tail, sgf_path):

    pgn_path = os.path.normpath(f"{sgf_path}//pgn//")
    players = dict()
    pattern_start = r";\s*P0\[0 Start P0\]"
    extracted_date = ".".join(filename.split("-")[-4:-1])
    gametype = ""
    extracted_white = ""
    extracted_black = ""
    res = resigned_or_drawn(sgf_tail)
    current = lines.popleft()

    while not re.match(pattern_start, current):
        if current.startswith("SU["):
            gametype = extract_gametype(current, expansions)
            if gametype.lower() == "hive-ultimate":
                print("Hive-Ultimate unsupported, skipping file")
                return

        elif current.startswith("RE["):
            if not res:
                res = current 
        elif current.startswith("P0[id") or current.startswith("P0[ id"):
            extracted_white = extract_player(current)
            players[extracted_white] = "1-0"
        elif current.startswith("P1[id") or current.startswith("P1[ id"):
            extracted_black = extract_player(current)
            players[extracted_black] = "0-1"
        current = lines.popleft()

    res = extract_result(res, players)
    sgf_body = lines
    date = f'[Date "{extracted_date}"]'
    event = f'[Event ""]'
    site = f'[Site "boardspace.net"]'
    game_round = f'[Round ""]'
    white = f'[White "{extracted_white}"]'
    black = f'[Black "{extracted_black}"]'
    result = f'[Result "{res}"]'

    with open(
        os.path.join(pgn_path, f"{filename}.pgn"), "w", encoding="utf-8"
    ) as file_write:
        file_write.write(
            f"{gametype}\n{date}\n{event}\n{site}\n{game_round}\n{white}\n{black}\n{result}\n\n"
        )

    append_moves(sgf_body, filename, expansions, pgn_path)


def extract_gametype(line, expansions):
    gametype = line[3:-2]
    if gametype == "Hive-Ultimate":
        return gametype 
    exp_pieces = ""

    if len(gametype) == 4:
        gametype = '[GameType "Base"]'
    else:
        for char in gametype[-3:]:
            char = char.upper()
            if char in expansions:
                expansions[char] += 1

        for k, v in expansions.items():
            if v:
                exp_pieces += k
        gametype = f'[GameType "Base+{exp_pieces}"]'
    return gametype


# try to see if the game finished by agreement
def resigned_or_drawn(sgf_tail):
    # regex that will handle result in games where resign or accept draw took place, this helps because it's more reliable than the result line in the sgf in some cases
    pattern_end = r"^; (P\d)\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$"

    match_end = re.match(pattern_end, sgf_tail)
    res = ""
    if match_end:
        player = match_end.group(1)
        outcome = match_end.group(2)
        if outcome.lower() != "resign":
            res = "1/2-1/2"
        else:
            if player == "P0":
                res = "0-1"
            else:
                res = "1-0"
    return res


# extract result from result line
def extract_result(line, players):
    res = line.split(" ")[-1][:-2]
    if res == "draw":
        res = "1/2-1/2"
    else:
        try:
            res = f"{players[res]}"

        # this will sometimes happen due to how boardspace saves results for guest games and games where the player who won was using a localized language version
        except KeyError:
            res = "error parsing result"
    return res


def extract_player(line):
    return line.split(" ")[-1][:-2].strip('"')


def append_moves(sgf_body, filename, expansions, pgn_path):

    end = r"(:?[Aa]ccept[dD]raw)|(:?[rR]esign)"
    i = 1
    lookup_table = defaultdict(list)
    reverse_lookup = {}
    placed_bug = ""
    destination = ""
    coordinates = ""
    draw = False

    with open(
        os.path.join(pgn_path, f"{filename}.pgn"), "a", encoding="utf-8"
    ) as file_write:
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
                i, placed_bug, destination, coordinates = append_current_move(
                    i,
                    placed_bug,
                    destination,
                    coordinates,
                    file_write,
                    lookup_table,
                    reverse_lookup,
                )

            # update the current move to be written
            elif low != "pass":
                placed_bug, coordinates, destination = extract_piece_and_destination(
                    i, line, expansions, lookup_table, reverse_lookup
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
        r".*P[01]\[\d+ ([dD]one).*$",
        r".*P\d\[\d+ ((?:[rR]esign)|(?:[Aa]ccept[Dd]raw)).*$",
        r".*P\d\[\d+ (?:[Dd]ecline)?(?:[Oo]ffer)?([Dd]raw)+.*$",
    ]
    for pattern in patterns:
        match_pattern = re.match(pattern, line)
        if match_pattern:
            return match_pattern.group(1)
    return ""


def append_current_move(
    i, placed_bug, destination, coordinates, file_write, lookup_table, reverse_lookup
):
    if not placed_bug:
        placed_bug = "pass"
        destination = ""
    file_write.write(f"{i}. {placed_bug} {destination}\n")
    if placed_bug in reverse_lookup:
        lookup_table[reverse_lookup[placed_bug]].pop()
    if placed_bug != "pass":
        reverse_lookup[placed_bug] = coordinates
        lookup_table[coordinates].append(placed_bug)
    i += 1
    placed_bug = destination = coordinates = ""
    return i, placed_bug, destination, coordinates


def extract_piece_and_destination(i, line, expansions, lookup_table, reverse_lookup):
    turn = line.split()
    placed_bug = turn[0]
    # strip extra number for l/m/p
    if len(placed_bug) != 1 and placed_bug[1] in expansions:
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
    return placed_bug, coordinates, destination


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
