from django.forms import RadioSelect

from .base import WidgetTest


class RadioSelectTest(WidgetTest):
    widget = RadioSelect

    def test_render(self):
        choices = (('', '------'),) + self.beatles
        self.check_html(self.widget(choices=choices), 'beatle', 'J', html=(
            """<ul>
            <li><label><input type="radio" name="beatle" value="" /> ------</label></li>
            <li><label><input checked type="radio" name="beatle" value="J" /> John</label></li>
            <li><label><input type="radio" name="beatle" value="P" /> Paul</label></li>
            <li><label><input type="radio" name="beatle" value="G" /> George</label></li>
            <li><label><input type="radio" name="beatle" value="R" /> Ringo</label></li>
            </ul>"""
        ))

    def test_nested_choices(self):
        nested_choices = (
            ('unknown', 'Unknown'),
            ('Audio', (('vinyl', 'Vinyl'), ('cd', 'CD'))),
            ('Video', (('vhs', 'VHS'), ('dvd', 'DVD'))),
        )
        html = """
        <ul id="media">
        <li>
        <label for="media_0"><input id="media_0" name="nestchoice" type="radio" value="unknown" /> Unknown</label>
        </li>
        <li>Audio<ul id="media_1">
        <li>
        <label for="media_1_0"><input id="media_1_0" name="nestchoice" type="radio" value="vinyl" /> Vinyl</label>
        </li>
        <li><label for="media_1_1"><input id="media_1_1" name="nestchoice" type="radio" value="cd" /> CD</label></li>
        </ul></li>
        <li>Video<ul id="media_2">
        <li><label for="media_2_0"><input id="media_2_0" name="nestchoice" type="radio" value="vhs" /> VHS</label></li>
        <li>
        <label for="media_2_1">
        <input checked id="media_2_1" name="nestchoice" type="radio" value="dvd" /> DVD
        </label>
        </li>
        </ul></li>
        </ul>
        """
        self.check_html(
            self.widget(choices=nested_choices), 'nestchoice', 'dvd',
            attrs={'id': 'media'}, html=html,
        )

    def test_constructor_attrs(self):
        """
        Attributes provided at instantiation are passed to the constituent
        inputs.
        """
        widget = RadioSelect(attrs={'id': 'foo'}, choices=self.beatles)
        html = """
        <ul id="foo">
        <li>
        <label for="foo_0"><input checked type="radio" id="foo_0" value="J" name="beatle" /> John</label>
        </li>
        <li><label for="foo_1"><input type="radio" id="foo_1" value="P" name="beatle" /> Paul</label></li>
        <li><label for="foo_2"><input type="radio" id="foo_2" value="G" name="beatle" /> George</label></li>
        <li><label for="foo_3"><input type="radio" id="foo_3" value="R" name="beatle" /> Ringo</label></li>
        </ul>
        """
        self.check_html(widget, 'beatle', 'J', html=html)

    def test_render_attrs(self):
        """
        Attributes provided at render-time are passed to the constituent
        inputs.
        """
        html = """
        <ul id="bar">
        <li>
        <label for="bar_0"><input checked type="radio" id="bar_0" value="J" name="beatle" /> John</label>
        </li>
        <li><label for="bar_1"><input type="radio" id="bar_1" value="P" name="beatle" /> Paul</label></li>
        <li><label for="bar_2"><input type="radio" id="bar_2" value="G" name="beatle" /> George</label></li>
        <li><label for="bar_3"><input type="radio" id="bar_3" value="R" name="beatle" /> Ringo</label></li>
        </ul>
        """
        self.check_html(self.widget(choices=self.beatles), 'beatle', 'J', attrs={'id': 'bar'}, html=html)
