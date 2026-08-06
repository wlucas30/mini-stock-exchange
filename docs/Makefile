.PHONY: all clean

all: commands.pdf

commands.pdf: commands.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error commands.tex

clean:
	latexmk -C
