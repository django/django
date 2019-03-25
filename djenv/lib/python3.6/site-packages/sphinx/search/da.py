# -*- coding: utf-8 -*-
"""
    sphinx.search.da
    ~~~~~~~~~~~~~~~~

    Danish search language: includes the JS Danish stemmer.

    :copyright: Copyright 2007-2013 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from sphinx.search import SearchLanguage, parse_stop_word

import snowballstemmer

if False:
    # For type annotation
    from typing import Any  # NOQA


danish_stopwords = parse_stop_word(u'''
| source: http://snowball.tartarus.org/algorithms/danish/stop.txt
og           | and
i            | in
jeg          | I
det          | that (dem. pronoun)/it (pers. pronoun)
at           | that (in front of a sentence)/to (with infinitive)
en           | a/an
den          | it (pers. pronoun)/that (dem. pronoun)
til          | to/at/for/until/against/by/of/into, more
er           | present tense of "to be"
som          | who, as
på           | on/upon/in/on/at/to/after/of/with/for, on
de           | they
med          | with/by/in, along
han          | he
af           | of/by/from/off/for/in/with/on, off
for          | at/for/to/from/by/of/ago, in front/before, because
ikke         | not
der          | who/which, there/those
var          | past tense of "to be"
mig          | me/myself
sig          | oneself/himself/herself/itself/themselves
men          | but
et           | a/an/one, one (number), someone/somebody/one
har          | present tense of "to have"
om           | round/about/for/in/a, about/around/down, if
vi           | we
min          | my
havde        | past tense of "to have"
ham          | him
hun          | she
nu           | now
over         | over/above/across/by/beyond/past/on/about, over/past
da           | then, when/as/since
fra          | from/off/since, off, since
du           | you
ud           | out
sin          | his/her/its/one's
dem          | them
os           | us/ourselves
op           | up
man          | you/one
hans         | his
hvor         | where
eller        | or
hvad         | what
skal         | must/shall etc.
selv         | myself/youself/herself/ourselves etc., even
her          | here
alle         | all/everyone/everybody etc.
vil          | will (verb)
blev         | past tense of "to stay/to remain/to get/to become"
kunne        | could
ind          | in
når          | when
være         | present tense of "to be"
dog          | however/yet/after all
noget        | something
ville        | would
jo           | you know/you see (adv), yes
deres        | their/theirs
efter        | after/behind/according to/for/by/from, later/afterwards
ned          | down
skulle       | should
denne        | this
end          | than
dette        | this
mit          | my/mine
også         | also
under        | under/beneath/below/during, below/underneath
have         | have
dig          | you
anden        | other
hende        | her
mine         | my
alt          | everything
meget        | much/very, plenty of
sit          | his, her, its, one's
sine         | his, her, its, one's
vor          | our
mod          | against
disse        | these
hvis         | if
din          | your/yours
nogle        | some
hos          | by/at
blive        | be/become
mange        | many
ad           | by/through
bliver       | present tense of "to be/to become"
hendes       | her/hers
været        | be
thi          | for (conj)
jer          | you
sådan        | such, like this/like that
''')

js_stemmer = u"""
var JSX={};(function(g){function j(b,e){var a=function(){};a.prototype=e.prototype;var c=new a;for(var d in b){b[d].prototype=c}}function I(c,b){for(var a in b.prototype)if(b.prototype.hasOwnProperty(a))c.prototype[a]=b.prototype[a]}function i(a,b,d){function c(a,b,c){delete a[b];a[b]=c;return c}Object.defineProperty(a,b,{get:function(){return c(a,b,d())},set:function(d){c(a,b,d)},enumerable:true,configurable:true})}function J(a,b,c){return a[b]=a[b]/c|0}var E=parseInt;var D=parseFloat;function K(a){return a!==a}var A=isFinite;var z=encodeURIComponent;var y=decodeURIComponent;var x=encodeURI;var w=decodeURI;var u=Object.prototype.toString;var C=Object.prototype.hasOwnProperty;function f(){}g.require=function(b){var a=p[b];return a!==undefined?a:null};g.profilerIsRunning=function(){return f.getResults!=null};g.getProfileResults=function(){return(f.getResults||function(){return{}})()};g.postProfileResults=function(a,b){if(f.postResults==null)throw new Error('profiler has not been turned on');return f.postResults(a,b)};g.resetProfileResults=function(){if(f.resetResults==null)throw new Error('profiler has not been turned on');return f.resetResults()};g.DEBUG=false;function t(){};j([t],Error);function b(a,b,c){this.G=a.length;this.S=a;this.V=b;this.J=c;this.I=null;this.W=null};j([b],Object);function l(){};j([l],Object);function d(){var a;var b;var c;this.F={};a=this.D='';b=this._=0;c=this.A=a.length;this.B=0;this.C=b;this.E=c};j([d],l);function v(a,b){a.D=b.D;a._=b._;a.A=b.A;a.B=b.B;a.C=b.C;a.E=b.E};function n(b,d,c,e){var a;if(b._>=b.A){return false}a=b.D.charCodeAt(b._);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._++;return true};function m(b,d,c,e){var a;if(b._<=b.B){return false}a=b.D.charCodeAt(b._-1);if(a>e||a<c){return false}a-=c;if((d[a>>>3]&1<<(a&7))===0){return false}b._--;return true};function r(a,d,c,e){var b;if(a._>=a.A){return false}b=a.D.charCodeAt(a._);if(b>e||b<c){a._++;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._++;return true}return false};function q(a,d,c,e){var b;if(a._<=a.B){return false}b=a.D.charCodeAt(a._-1);if(b>e||b<c){a._--;return true}b-=c;if((d[b>>>3]&1<<(b&7))===0){a._--;return true}return false};function h(a,b,d){var c;if(a._-a.B<b){return false}if(a.D.slice((c=a._)-b,c)!==d){return false}a._-=b;return true};function e(d,m,p){var b;var g;var e;var n;var f;var k;var l;var i;var h;var c;var a;var j;var o;b=0;g=p;e=d._;n=d.B;f=0;k=0;l=false;while(true){i=b+(g-b>>1);h=0;c=f<k?f:k;a=m[i];for(j=a.G-1-c;j>=0;j--){if(e-c===n){h=-1;break}h=d.D.charCodeAt(e-1-c)-a.S.charCodeAt(j);if(h!==0){break}c++}if(h<0){g=i;k=c}else{b=i;f=c}if(g-b<=1){if(b>0){break}if(g===b){break}if(l){break}l=true}}while(true){a=m[b];if(f>=a.G){d._=e-a.G|0;if(a.I==null){return a.J}o=a.I(d);d._=e-a.G|0;if(o){return a.J}}b=a.V;if(b<0){return 0}}return-1};function s(a,b,d,e){var c;c=e.length-(d-b);a.D=a.D.slice(0,b)+e+a.D.slice(d);a.A+=c|0;if(a._>=d){a._+=c|0}else if(a._>b){a._=b}return c|0};function c(a,f){var b;var c;var d;var e;b=false;if((c=a.C)<0||c>(d=a.E)||d>(e=a.A)||e>a.D.length?false:true){s(a,a.C,a.E,f);b=true}return b};function o(a,f){var b;var c;var d;var e;b='';if((c=a.C)<0||c>(d=a.E)||d>(e=a.A)||e>a.D.length?false:true){b=a.D.slice(a.C,a.E)}return b};d.prototype.H=function(){return false};d.prototype.T=function(b){var a;var c;var d;var e;a=this.F['.'+b];if(a==null){c=this.D=b;d=this._=0;e=this.A=c.length;this.B=0;this.C=d;this.E=e;this.H();a=this.D;this.F['.'+b]=a}return a};d.prototype.stemWord=d.prototype.T;d.prototype.U=function(e){var d;var b;var c;var a;var f;var g;var h;d=[];for(b=0;b<e.length;b++){c=e[b];a=this.F['.'+c];if(a==null){f=this.D=c;g=this._=0;h=this.A=f.length;this.B=0;this.C=g;this.E=h;this.H();a=this.D;this.F['.'+c]=a}d.push(a)}return d};d.prototype.stemWords=d.prototype.U;function a(){d.call(this);this.I_x=0;this.I_p1=0;this.S_ch=''};j([a],d);a.prototype.K=function(a){this.I_x=a.I_x;this.I_p1=a.I_p1;this.S_ch=a.S_ch;v(this,a)};a.prototype.copy_from=a.prototype.K;a.prototype.P=function(){var g;var d;var b;var e;var c;var f;var i;var j;var k;var h;this.I_p1=j=this.A;g=i=this._;b=i+3|0;if(0>b||b>j){return false}h=this._=b;this.I_x=h;this._=g;a:while(true){d=this._;e=true;b:while(e===true){e=false;if(!n(this,a.g_v,97,248)){break b}this._=d;break a}k=this._=d;if(k>=this.A){return false}this._++}a:while(true){c=true;b:while(c===true){c=false;if(!r(this,a.g_v,97,248)){break b}break a}if(this._>=this.A){return false}this._++}this.I_p1=this._;f=true;a:while(f===true){f=false;if(!(this.I_p1<this.I_x)){break a}this.I_p1=this.I_x}return true};a.prototype.r_mark_regions=a.prototype.P;function G(b){var h;var e;var c;var f;var d;var g;var j;var k;var l;var i;b.I_p1=k=b.A;h=j=b._;c=j+3|0;if(0>c||c>k){return false}i=b._=c;b.I_x=i;b._=h;a:while(true){e=b._;f=true;b:while(f===true){f=false;if(!n(b,a.g_v,97,248)){break b}b._=e;break a}l=b._=e;if(l>=b.A){return false}b._++}a:while(true){d=true;b:while(d===true){d=false;if(!r(b,a.g_v,97,248)){break b}break a}if(b._>=b.A){return false}b._++}b.I_p1=b._;g=true;a:while(g===true){g=false;if(!(b.I_p1<b.I_x)){break a}b.I_p1=b.I_x}return true};a.prototype.O=function(){var b;var f;var d;var g;var h;var i;f=this.A-(g=this._);if(g<this.I_p1){return false}h=this._=this.I_p1;d=this.B;this.B=h;i=this._=this.A-f;this.E=i;b=e(this,a.a_0,32);if(b===0){this.B=d;return false}this.C=this._;this.B=d;switch(b){case 0:return false;case 1:if(!c(this,'')){return false}break;case 2:if(!m(this,a.g_s_ending,97,229)){return false}if(!c(this,'')){return false}break}return true};a.prototype.r_main_suffix=a.prototype.O;function H(b){var d;var g;var f;var h;var i;var j;g=b.A-(h=b._);if(h<b.I_p1){return false}i=b._=b.I_p1;f=b.B;b.B=i;j=b._=b.A-g;b.E=j;d=e(b,a.a_0,32);if(d===0){b.B=f;return false}b.C=b._;b.B=f;switch(d){case 0:return false;case 1:if(!c(b,'')){return false}break;case 2:if(!m(b,a.g_s_ending,97,229)){return false}if(!c(b,'')){return false}break}return true};a.prototype.N=function(){var f;var g;var b;var h;var d;var i;var j;var k;var l;f=(h=this.A)-(d=this._);g=h-d;if(d<this.I_p1){return false}i=this._=this.I_p1;b=this.B;this.B=i;j=this._=this.A-g;this.E=j;if(e(this,a.a_1,4)===0){this.B=b;return false}this.C=this._;l=this.B=b;k=this._=this.A-f;if(k<=l){return false}this._--;this.C=this._;return!c(this,'')?false:true};a.prototype.r_consonant_pair=a.prototype.N;function k(b){var i;var j;var d;var g;var f;var k;var l;var m;var h;i=(g=b.A)-(f=b._);j=g-f;if(f<b.I_p1){return false}k=b._=b.I_p1;d=b.B;b.B=k;l=b._=b.A-j;b.E=l;if(e(b,a.a_1,4)===0){b.B=d;return false}b.C=b._;h=b.B=d;m=b._=b.A-i;if(m<=h){return false}b._--;b.C=b._;return!c(b,'')?false:true};a.prototype.Q=function(){var f;var l;var m;var d;var j;var b;var g;var n;var i;var p;var o;l=this.A-this._;b=true;a:while(b===true){b=false;this.E=this._;if(!h(this,2,'st')){break a}this.C=this._;if(!h(this,2,'ig')){break a}if(!c(this,'')){return false}}i=this._=(n=this.A)-l;m=n-i;if(i<this.I_p1){return false}p=this._=this.I_p1;d=this.B;this.B=p;o=this._=this.A-m;this.E=o;f=e(this,a.a_2,5);if(f===0){this.B=d;return false}this.C=this._;this.B=d;switch(f){case 0:return false;case 1:if(!c(this,'')){return false}j=this.A-this._;g=true;a:while(g===true){g=false;if(!k(this)){break a}}this._=this.A-j;break;case 2:if(!c(this,'løs')){return false}break}return true};a.prototype.r_other_suffix=a.prototype.Q;function F(b){var d;var p;var m;var f;var l;var g;var i;var o;var j;var q;var n;p=b.A-b._;g=true;a:while(g===true){g=false;b.E=b._;if(!h(b,2,'st')){break a}b.C=b._;if(!h(b,2,'ig')){break a}if(!c(b,'')){return false}}j=b._=(o=b.A)-p;m=o-j;if(j<b.I_p1){return false}q=b._=b.I_p1;f=b.B;b.B=q;n=b._=b.A-m;b.E=n;d=e(b,a.a_2,5);if(d===0){b.B=f;return false}b.C=b._;b.B=f;switch(d){case 0:return false;case 1:if(!c(b,'')){return false}l=b.A-b._;i=true;a:while(i===true){i=false;if(!k(b)){break a}}b._=b.A-l;break;case 2:if(!c(b,'løs')){return false}break}return true};a.prototype.R=function(){var e;var b;var d;var f;var g;var i;var j;e=this.A-(f=this._);if(f<this.I_p1){return false}g=this._=this.I_p1;b=this.B;this.B=g;i=this._=this.A-e;this.E=i;if(!q(this,a.g_v,97,248)){this.B=b;return false}this.C=this._;j=this.S_ch=o(this,this.S_ch);if(j===''){return false}this.B=b;return!(d=this.S_ch,h(this,d.length,d))?false:!c(this,'')?false:true};a.prototype.r_undouble=a.prototype.R;function B(b){var f;var d;var e;var g;var i;var j;var k;f=b.A-(g=b._);if(g<b.I_p1){return false}i=b._=b.I_p1;d=b.B;b.B=i;j=b._=b.A-f;b.E=j;if(!q(b,a.g_v,97,248)){b.B=d;return false}b.C=b._;k=b.S_ch=o(b,b.S_ch);if(k===''){return false}b.B=d;return!(e=b.S_ch,h(b,e.length,e))?false:!c(b,'')?false:true};a.prototype.H=function(){var i;var g;var h;var j;var b;var c;var d;var a;var e;var l;var m;var n;var o;var p;var q;var f;i=this._;b=true;a:while(b===true){b=false;if(!G(this)){break a}}l=this._=i;this.B=l;n=this._=m=this.A;g=m-n;c=true;a:while(c===true){c=false;if(!H(this)){break a}}p=this._=(o=this.A)-g;h=o-p;d=true;a:while(d===true){d=false;if(!k(this)){break a}}f=this._=(q=this.A)-h;j=q-f;a=true;a:while(a===true){a=false;if(!F(this)){break a}}this._=this.A-j;e=true;a:while(e===true){e=false;if(!B(this)){break a}}this._=this.B;return true};a.prototype.stem=a.prototype.H;a.prototype.L=function(b){return b instanceof a};a.prototype.equals=a.prototype.L;a.prototype.M=function(){var c;var a;var b;var d;c='DanishStemmer';a=0;for(b=0;b<c.length;b++){d=c.charCodeAt(b);a=(a<<5)-a+d;a=a&a}return a|0};a.prototype.hashCode=a.prototype.M;a.serialVersionUID=1;i(a,'methodObject',function(){return new a});i(a,'a_0',function(){return[new b('hed',-1,1),new b('ethed',0,1),new b('ered',-1,1),new b('e',-1,1),new b('erede',3,1),new b('ende',3,1),new b('erende',5,1),new b('ene',3,1),new b('erne',3,1),new b('ere',3,1),new b('en',-1,1),new b('heden',10,1),new b('eren',10,1),new b('er',-1,1),new b('heder',13,1),new b('erer',13,1),new b('s',-1,2),new b('heds',16,1),new b('es',16,1),new b('endes',18,1),new b('erendes',19,1),new b('enes',18,1),new b('ernes',18,1),new b('eres',18,1),new b('ens',16,1),new b('hedens',24,1),new b('erens',24,1),new b('ers',16,1),new b('ets',16,1),new b('erets',28,1),new b('et',-1,1),new b('eret',30,1)]});i(a,'a_1',function(){return[new b('gd',-1,-1),new b('dt',-1,-1),new b('gt',-1,-1),new b('kt',-1,-1)]});i(a,'a_2',function(){return[new b('ig',-1,1),new b('lig',0,1),new b('elig',1,1),new b('els',-1,1),new b('løst',-1,2)]});i(a,'g_v',function(){return[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,0,48,0,128]});i(a,'g_s_ending',function(){return[239,254,42,3,0,0,0,0,0,0,0,0,0,0,0,0,16]});var p={'src/stemmer.jsx':{Stemmer:l},'src/danish-stemmer.jsx':{DanishStemmer:a}}}(JSX))
var Stemmer = JSX.require("src/danish-stemmer.jsx").DanishStemmer;
"""


class SearchDanish(SearchLanguage):
    lang = 'da'
    language_name = 'Danish'
    js_stemmer_rawcode = 'danish-stemmer.js'
    js_stemmer_code = js_stemmer
    stopwords = danish_stopwords

    def init(self, options):
        # type: (Any) -> None
        self.stemmer = snowballstemmer.stemmer('danish')

    def stem(self, word):
        # type: (unicode) -> unicode
        return self.stemmer.stemWord(word.lower())
