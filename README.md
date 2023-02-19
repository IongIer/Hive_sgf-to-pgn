# Hive_sgf-to-pgn

Convert [Hive games](https://www.boardspace.net/hive/hivegames/) played on boardspace from sgf to pgn files that can be opened in other applications such as [Mzinga](https://github.com/jonthysell/Mzinga/).

Will convert all the sgf files (skipping Hive-Ultimate games) in the provided path and save them in a new pgn folder created in that path.

Usage:
python hive_sgf-to-pgn.py -path "path to sgf files"

No dependencies only standard library is used.

Current known limitations:

1. Fails on older games, should work on games played after 2018
2. Will only work on games downloaded through the boardspace site, games saved from the app have a slightly different format
3. Sometimes it won't be able to figure out game result due to how boardspace saves the files
4. Can't handle Hive Ultimate but pgn viewers don't support it either
