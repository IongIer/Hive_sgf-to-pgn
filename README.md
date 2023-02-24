# Hive_sgf-to-pgn

Convert [Hive](https://boardgamegeek.com/boardgame/2655/hive) games played on [boardspace](https://www.boardspace.net) from sgf to pgn files that can be opened in other applications such as [Mzinga](https://github.com/jonthysell/Mzinga/).

Will convert all the sgf files (skipping Hive-Ultimate games) in the provided path and save them in a new pgn folder created in that path.

Usage:
python hive_sgf-to-pgn.py -path "path to sgf files"

No dependencies only standard library is used.

Current known limitations:

1. Fails on older games, should work on games played after 2018
2. Works for [games](https://www.boardspace.net/hive/hivegames/) downloaded through the boardspace site, games saved from the app have a slightly different format but now should work as well. However I haven't thoroughly tested on games downloaded from the app + those have no result in the header, it's better to just get them from the site
3. Sometimes it won't be able to figure out game result due to how boardspace saves the files
4. Can't handle Hive Ultimate but pgn viewers don't support it either
