===========================
Outputting PDFs with Django
===========================

This document explains how to output PDF files dynamically using Django views.
This is made possible by the excellent, open-source ReportLab_ Python PDF
library.

The advantage of generating PDF files dynamically is that you can create
customized PDFs for different purposes -- say, for different users or different
pieces of content.

For example, Django was used at kusports.com_ to generate customized,
printer-friendly NCAA tournament brackets, as PDF files, for people
participating in a March Madness contest.

.. _ReportLab: http://www.reportlab.com/software/opensource/rl-toolkit/
.. _kusports.com: http://www.kusports.com/

Install ReportLab
=================

Download and install the ReportLab library from
http://www.reportlab.com/software/opensource/rl-toolkit/download/.
The `user guide`_ (not coincidentally, a PDF file) explains how to install it.
Alternatively, you can also install it with ``pip``:

.. code-block:: bash

    $ sudo pip install reportlab

Test your installation by importing it in the Python interactive interpreter::

    >>> import reportlab

If that command doesn't raise any errors, the installation worked.

.. _user guide: http://www.reportlab.com/docs/reportlab-userguide.pdf

Write your view
===============

The key to generating PDFs dynamically with Django is that the ReportLab API
acts on file-like objects, and Django's :class:`~django.http.HttpResponse`
objects are file-like objects.

Here's a "Hello World" example::

    from reportlab.pdfgen import canvas
    from django.http import HttpResponse

    def some_view(request):
        # Create the HttpResponse object with the appropriate PDF headers.
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="somefilename.pdf"'

        # Create the PDF object, using the response object as its "file."
        p = canvas.Canvas(response)

        # Draw things on the PDF. Here's where the PDF generation happens.
        # See the ReportLab documentation for the full list of functionality.
        p.drawString(100, 100, "Hello world.")

        # Close the PDF object cleanly, and we're done.
        p.showPage()
        p.save()
        return response

The code and comments should be self-explanatory, but a few things deserve a
mention:

* The response gets a special MIME type, :mimetype:`application/pdf`. This
  tells browsers that the document is a PDF file, rather than an HTML file.
  If you leave this off, browsers will probably interpret the output as
  HTML, which would result in ugly, scary gobbledygook in the browser
  window.

* The response gets an additional ``Content-Disposition`` header, which
  contains the name of the PDF file. This filename is arbitrary: Call it
  whatever you want. It'll be used by browsers in the "Save as..."
  dialogue, etc.

* The ``Content-Disposition`` header starts with ``'attachment; '`` in this
  example. This forces Web browsers to pop-up a dialog box
  prompting/confirming how to handle the document even if a default is set
  on the machine. If you leave off ``'attachment;'``, browsers will handle
  the PDF using whatever program/plugin they've been configured to use for
  PDFs. Here's what that code would look like::

      response['Content-Disposition'] = 'filename="somefilename.pdf"'

* Hooking into the ReportLab API is easy: Just pass ``response`` as the
  first argument to ``canvas.Canvas``. The ``Canvas`` class expects a
  file-like object, and :class:`~django.http.HttpResponse` objects fit the
  bill.

* Note that all subsequent PDF-generation methods are called on the PDF
  object (in this case, ``p``) -- not on ``response``.

* Finally, it's important to call ``showPage()`` and ``save()`` on the PDF
  file.

.. note::

    ReportLab is not thread-safe. Some of our users have reported odd issues
    with building PDF-generating Django views that are accessed by many people
    at the same time.

Complex PDFs
============

If you're creating a complex PDF document with ReportLab, consider using the
:mod:`io` library as a temporary holding place for your PDF file. This
library provides a file-like object interface that is particularly efficient.
Here's the above "Hello World" example rewritten to use :mod:`io`::

    from io import BytesIO
    from reportlab.pdfgen import canvas
    from django.http import HttpResponse

    def some_view(request):
        # Create the HttpResponse object with the appropriate PDF headers.
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="somefilename.pdf"'

        buffer = BytesIO()

        # Create the PDF object, using the BytesIO object as its "file."
        p = canvas.Canvas(buffer)

        # Draw things on the PDF. Here's where the PDF generation happens.
        # See the ReportLab documentation for the full list of functionality.
        p.drawString(100, 100, "Hello world.")

        # Close the PDF object cleanly.
        p.showPage()
        p.save()

        # Get the value of the BytesIO buffer and write it to the response.
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response

Further resources
=================

* PDFlib_ is another PDF-generation library that has Python bindings. To
  use it with Django, just use the same concepts explained in this article.
* `Pisa XHTML2PDF`_ is yet another PDF-generation library. Pisa ships with
  an example of how to integrate Pisa with Django.
* HTMLdoc_ is a command-line script that can convert HTML to PDF. It
  doesn't have a Python interface, but you can escape out to the shell
  using ``system`` or ``popen`` and retrieve the output in Python.

.. _PDFlib: http://www.pdflib.org/
.. _`Pisa XHTML2PDF`: http://www.xhtml2pdf.com/
.. _HTMLdoc: http://www.htmldoc.org/

Other formats
=============

Notice that there isn't a lot in these examples that's PDF-specific -- just the
bits using ``reportlab``. You can use a similar technique to generate any
arbitrary format that you can find a Python library for. Also see
:doc:`/howto/outputting-csv` for another example and some techniques you can use
when generated text-based formats.
