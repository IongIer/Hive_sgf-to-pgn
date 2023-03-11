# Hive_sgf-to-pgn

Convert [Hive](https://boardgamegeek.com/boardgame/2655/hive) games played on [boardspace](https://www.boardspace.net) from sgf to pgn files that can be opened in other applications such as [Mzinga](https://github.com/jonthysell/Mzinga/).

Will convert all the sgf files (skipping Hive-Ultimate games) in the provided path and save them in a new pgn folder created in that path.

Usage:
python hive_sgf-to-pgn.py -path "path to sgf files"

No dependencies only standard library is used.

Current known limitations:

1. Sometimes it won't be able to figure out game result due to how boardspace saves the files
2. Can't handle Hive Ultimate but pgn viewers don't support it either
3. Games before march 2013 that contain a pillbug will not be valid because pillbug used different rules
