from django.contrib.comments.forms import CommentForm
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.template import Template, Context
from regressiontests.comment_tests.models import Article, Author
from regressiontests.comment_tests.tests import CommentTestCase

class CommentTemplateTagTests(CommentTestCase):

    def render(self, t, **c):
        ctx = Context(c)
        out = Template(t).render(ctx)
        return ctx, out

    def testCommentFormTarget(self):
        ctx, out = self.render("{% load comments %}{% comment_form_target %}")
        self.assertEqual(out, "/post/")

    def testGetCommentForm(self, tag=None):
        t = "{% load comments %}" + (tag or "{% get_comment_form for comment_tests.article a.id as form %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "")
        self.assert_(isinstance(ctx["form"], CommentForm))

    def testGetCommentFormFromLiteral(self):
        self.testGetCommentForm("{% get_comment_form for comment_tests.article 1 as form %}")

    def testGetCommentFormFromObject(self):
        self.testGetCommentForm("{% get_comment_form for a as form %}")

    def testRenderCommentForm(self, tag=None):
        t = "{% load comments %}" + (tag or "{% render_comment_form for comment_tests.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assert_(out.strip().startswith("<form action="))
        self.assert_(out.strip().endswith("</form>"))

    def testRenderCommentFormFromLiteral(self):
        self.testRenderCommentForm("{% render_comment_form for comment_tests.article 1 %}")

    def testRenderCommentFormFromObject(self):
        self.testRenderCommentForm("{% render_comment_form for a %}")

    def testGetCommentCount(self, tag=None):
        self.createSomeComments()
        t = "{% load comments %}" + (tag or "{% get_comment_count for comment_tests.article a.id as cc %}") + "{{ cc }}"
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assertEqual(out, "2")

    def testGetCommentCountFromLiteral(self):
        self.testGetCommentCount("{% get_comment_count for comment_tests.article 1 as cc %}")

    def testGetCommentCountFromObject(self):
        self.testGetCommentCount("{% get_comment_count for a as cc %}")

    def testGetCommentList(self, tag=None):
        c1, c2, c3, c4 = self.createSomeComments()
        t = "{% load comments %}" + (tag or "{% get_comment_list for comment_tests.author a.id as cl %}")
        ctx, out = self.render(t, a=Author.objects.get(pk=1))
        self.assertEqual(out, "")
        self.assertEqual(list(ctx["cl"]), [c2])

    def testGetCommentListFromLiteral(self):
        self.testGetCommentList("{% get_comment_list for comment_tests.author 1 as cl %}")

    def testGetCommentListFromObject(self):
        self.testGetCommentList("{% get_comment_list for a as cl %}")

    def testGetCommentPermalink(self):
        self.createSomeComments()
        t = "{% load comments %}{% get_comment_list for comment_tests.author author.id as cl %}"
        t += "{% get_comment_permalink cl.0 %}"
        ct = ContentType.objects.get_for_model(Author)
        author = Author.objects.get(pk=1)
        ctx, out = self.render(t, author=author)
        self.assertEqual(out, "/cr/%s/%s/#c2" % (ct.id, author.id))

    def testGetCommentPermalinkFormatted(self):
        self.createSomeComments()
        t = "{% load comments %}{% get_comment_list for comment_tests.author author.id as cl %}"
        t += "{% get_comment_permalink cl.0 '#c%(id)s-by-%(user_name)s' %}"
        ct = ContentType.objects.get_for_model(Author)
        author = Author.objects.get(pk=1)
        ctx, out = self.render(t, author=author)
        self.assertEqual(out, "/cr/%s/%s/#c2-by-Joe Somebody" % (ct.id, author.id))

    def testRenderCommentList(self, tag=None):
        t = "{% load comments %}" + (tag or "{% render_comment_list for comment_tests.article a.id %}")
        ctx, out = self.render(t, a=Article.objects.get(pk=1))
        self.assert_(out.strip().startswith("<dl id=\"comments\">"))
        self.assert_(out.strip().endswith("</dl>"))

    def testRenderCommentListFromLiteral(self):
        self.testRenderCommentList("{% render_comment_list for comment_tests.article 1 %}")

    def testRenderCommentListFromObject(self):
        self.testRenderCommentList("{% render_comment_list for a %}")

