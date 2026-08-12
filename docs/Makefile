.PHONY: all clean

all: commands.pdf agents.pdf

commands.pdf: commands.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error commands.tex

agents.pdf: agents.tex
	latexmk -pdf -interaction=nonstopmode -halt-on-error agents.tex

clean:
	latexmk -C
