# Makefile for Sphinx LaTeX output

ALLDOCS = $(basename $(wildcard *.tex))
ALLPDF = $(addsuffix .pdf,$(ALLDOCS))
ALLDVI = $(addsuffix .dvi,$(ALLDOCS))
ALLPS  = $(addsuffix .ps,$(ALLDOCS))

# Prefix for archive names
ARCHIVEPREFIX =
# Additional LaTeX options
LATEXOPTS =
# format: pdf or dvi
FMT = pdf

LATEX = latex
PDFLATEX = {{ latex_engine }}
MAKEINDEX = makeindex

{% if latex_engine == 'platex' %}
all: all-pdf-ja
all-pdf: all-pdf-ja
{% else %}
all: $(ALLPDF)
all-pdf: $(ALLPDF)
{% endif -%}
all-dvi: $(ALLDVI)
all-ps: $(ALLPS)

all-pdf-ja:
	for f in *.pdf *.png *.gif *.jpg *.jpeg; do extractbb $$f; done
	for f in *.tex; do platex -kanji=utf8 $(LATEXOPTS) $$f; done
	for f in *.tex; do platex -kanji=utf8 $(LATEXOPTS) $$f; done
	for f in *.tex; do platex -kanji=utf8 $(LATEXOPTS) $$f; done
	-for f in *.idx; do mendex -U -f -d "`basename $$f .idx`.dic" -s python.ist $$f; done
	for f in *.tex; do platex -kanji=utf8 $(LATEXOPTS) $$f; done
	for f in *.tex; do platex -kanji=utf8 $(LATEXOPTS) $$f; done
	for f in *.dvi; do dvipdfmx $$f; done

zip: all-$(FMT)
	mkdir $(ARCHIVEPREFIX)docs-$(FMT)
	cp $(ALLPDF) $(ARCHIVEPREFIX)docs-$(FMT)
	zip -q -r -9 $(ARCHIVEPREFIX)docs-$(FMT).zip $(ARCHIVEPREFIX)docs-$(FMT)
	rm -r $(ARCHIVEPREFIX)docs-$(FMT)

tar: all-$(FMT)
	mkdir $(ARCHIVEPREFIX)docs-$(FMT)
	cp $(ALLPDF) $(ARCHIVEPREFIX)docs-$(FMT)
	tar cf $(ARCHIVEPREFIX)docs-$(FMT).tar $(ARCHIVEPREFIX)docs-$(FMT)
	rm -r $(ARCHIVEPREFIX)docs-$(FMT)

gz: tar
	gzip -9 < $(ARCHIVEPREFIX)docs-$(FMT).tar > $(ARCHIVEPREFIX)docs-$(FMT).tar.gz

bz2: tar
	bzip2 -9 -k $(ARCHIVEPREFIX)docs-$(FMT).tar

xz: tar
	xz -9 -k $(ARCHIVEPREFIX)docs-$(FMT).tar

# The number of LaTeX runs is quite conservative, but I don't expect it
# to get run often, so the little extra time won't hurt.
%.dvi: %.tex
	$(LATEX) $(LATEXOPTS) '$<'
	$(LATEX) $(LATEXOPTS) '$<'
	$(LATEX) $(LATEXOPTS) '$<'
	-$(MAKEINDEX) -s python.ist '$(basename $<).idx'
	$(LATEX) $(LATEXOPTS) '$<'
	$(LATEX) $(LATEXOPTS) '$<'

%.pdf: %.tex
	$(PDFLATEX) $(LATEXOPTS) '$<'
	$(PDFLATEX) $(LATEXOPTS) '$<'
	$(PDFLATEX) $(LATEXOPTS) '$<'
	-$(MAKEINDEX) -s python.ist '$(basename $<).idx'
	$(PDFLATEX) $(LATEXOPTS) '$<'
	$(PDFLATEX) $(LATEXOPTS) '$<'

%.ps: %.dvi
	dvips '$<'

clean:
	rm -f *.log *.ind *.aux *.toc *.syn *.idx *.out *.ilg *.pla *.ps *.tar *.tar.gz *.tar.bz2 *.tar.xz $(ALLPDF) $(ALLDVI)

.PHONY: all all-pdf all-dvi all-ps clean zip tar gz bz2 xz
.PHONY: all-pdf-ja

