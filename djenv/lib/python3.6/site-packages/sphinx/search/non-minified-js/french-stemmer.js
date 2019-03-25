// generatedy by JSX compiler 0.9.89 (2014-05-20 06:01:03 +0900; 8e8c6105f36f3dfe440ea026a3c93a3444977102)
var JSX = {};
(function (JSX) {
/**
 * extends the class
 */
function $__jsx_extend(derivations, base) {
	var ctor = function () {};
	ctor.prototype = base.prototype;
	var proto = new ctor();
	for (var i in derivations) {
		derivations[i].prototype = proto;
	}
}

/**
 * copies the implementations from source interface to target
 */
function $__jsx_merge_interface(target, source) {
	for (var k in source.prototype)
		if (source.prototype.hasOwnProperty(k))
			target.prototype[k] = source.prototype[k];
}

/**
 * defers the initialization of the property
 */
function $__jsx_lazy_init(obj, prop, func) {
	function reset(obj, prop, value) {
		delete obj[prop];
		obj[prop] = value;
		return value;
	}

	Object.defineProperty(obj, prop, {
		get: function () {
			return reset(obj, prop, func());
		},
		set: function (v) {
			reset(obj, prop, v);
		},
		enumerable: true,
		configurable: true
	});
}

var $__jsx_imul = Math.imul;
if (typeof $__jsx_imul === "undefined") {
	$__jsx_imul = function (a, b) {
		var ah  = (a >>> 16) & 0xffff;
		var al = a & 0xffff;
		var bh  = (b >>> 16) & 0xffff;
		var bl = b & 0xffff;
		return ((al * bl) + (((ah * bl + al * bh) << 16) >>> 0)|0);
	};
}

/**
 * fused int-ops with side-effects
 */
function $__jsx_ipadd(o, p, r) {
	return o[p] = (o[p] + r) | 0;
}
function $__jsx_ipsub(o, p, r) {
	return o[p] = (o[p] - r) | 0;
}
function $__jsx_ipmul(o, p, r) {
	return o[p] = $__jsx_imul(o[p], r);
}
function $__jsx_ipdiv(o, p, r) {
	return o[p] = (o[p] / r) | 0;
}
function $__jsx_ipmod(o, p, r) {
	return o[p] = (o[p] % r) | 0;
}
function $__jsx_ippostinc(o, p) {
	var v = o[p];
	o[p] = (v + 1) | 0;
	return v;
}
function $__jsx_ippostdec(o, p) {
	var v = o[p];
	o[p] = (v - 1) | 0;
	return v;
}

/**
 * non-inlined version of Array#each
 */
function $__jsx_forEach(o, f) {
	var l = o.length;
	for (var i = 0; i < l; ++i)
		f(o[i]);
}

/*
 * global functions, renamed to avoid conflict with local variable names
 */
var $__jsx_parseInt = parseInt;
var $__jsx_parseFloat = parseFloat;
function $__jsx_isNaN(n) { return n !== n; }
var $__jsx_isFinite = isFinite;

var $__jsx_encodeURIComponent = encodeURIComponent;
var $__jsx_decodeURIComponent = decodeURIComponent;
var $__jsx_encodeURI = encodeURI;
var $__jsx_decodeURI = decodeURI;

var $__jsx_ObjectToString = Object.prototype.toString;
var $__jsx_ObjectHasOwnProperty = Object.prototype.hasOwnProperty;

/*
 * profiler object, initialized afterwards
 */
function $__jsx_profiler() {
}

/*
 * public interface to JSX code
 */
JSX.require = function (path) {
	var m = $__jsx_classMap[path];
	return m !== undefined ? m : null;
};

JSX.profilerIsRunning = function () {
	return $__jsx_profiler.getResults != null;
};

JSX.getProfileResults = function () {
	return ($__jsx_profiler.getResults || function () { return {}; })();
};

JSX.postProfileResults = function (url, cb) {
	if ($__jsx_profiler.postResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.postResults(url, cb);
};

JSX.resetProfileResults = function () {
	if ($__jsx_profiler.resetResults == null)
		throw new Error("profiler has not been turned on");
	return $__jsx_profiler.resetResults();
};
JSX.DEBUG = false;
var GeneratorFunction$0 = 
(function () {
  try {
    return Function('import {GeneratorFunction} from "std:iteration"; return GeneratorFunction')();
  } catch (e) {
    return function GeneratorFunction () {};
  }
})();
var __jsx_generator_object$0 = 
(function () {
  function __jsx_generator_object() {
  	this.__next = 0;
  	this.__loop = null;
	this.__seed = null;
  	this.__value = undefined;
  	this.__status = 0;	// SUSPENDED: 0, ACTIVE: 1, DEAD: 2
  }

  __jsx_generator_object.prototype.next = function (seed) {
  	switch (this.__status) {
  	case 0:
  		this.__status = 1;
  		this.__seed = seed;

  		// go next!
  		this.__loop(this.__next);

  		var done = false;
  		if (this.__next != -1) {
  			this.__status = 0;
  		} else {
  			this.__status = 2;
  			done = true;
  		}
  		return { value: this.__value, done: done };
  	case 1:
  		throw new Error("Generator is already running");
  	case 2:
  		throw new Error("Generator is already finished");
  	default:
  		throw new Error("Unexpected generator internal state");
  	}
  };

  return __jsx_generator_object;
}());
function Among(s, substring_i, result) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = null;
	this.instance = null;
};

function Among$0(s, substring_i, result, method, instance) {
	this.s_size = s.length;
	this.s = s;
	this.substring_i = substring_i;
	this.result = result;
	this.method = method;
	this.instance = instance;
};

$__jsx_extend([Among, Among$0], Object);
function Stemmer() {
};

$__jsx_extend([Stemmer], Object);
function BaseStemmer() {
	var current$0;
	var cursor$0;
	var limit$0;
	this.cache = ({  });
	current$0 = this.current = "";
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};

$__jsx_extend([BaseStemmer], Stemmer);
BaseStemmer.prototype.setCurrent$S = function (value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = this.current = value;
	cursor$0 = this.cursor = 0;
	limit$0 = this.limit = current$0.length;
	this.limit_backward = 0;
	this.bra = cursor$0;
	this.ket = limit$0;
};


function BaseStemmer$setCurrent$LBaseStemmer$S($this, value) {
	var current$0;
	var cursor$0;
	var limit$0;
	current$0 = $this.current = value;
	cursor$0 = $this.cursor = 0;
	limit$0 = $this.limit = current$0.length;
	$this.limit_backward = 0;
	$this.bra = cursor$0;
	$this.ket = limit$0;
};

BaseStemmer.setCurrent$LBaseStemmer$S = BaseStemmer$setCurrent$LBaseStemmer$S;

BaseStemmer.prototype.getCurrent$ = function () {
	return this.current;
};


function BaseStemmer$getCurrent$LBaseStemmer$($this) {
	return $this.current;
};

BaseStemmer.getCurrent$LBaseStemmer$ = BaseStemmer$getCurrent$LBaseStemmer$;

BaseStemmer.prototype.copy_from$LBaseStemmer$ = function (other) {
	this.current = other.current;
	this.cursor = other.cursor;
	this.limit = other.limit;
	this.limit_backward = other.limit_backward;
	this.bra = other.bra;
	this.ket = other.ket;
};


function BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$($this, other) {
	$this.current = other.current;
	$this.cursor = other.cursor;
	$this.limit = other.limit;
	$this.limit_backward = other.limit_backward;
	$this.bra = other.bra;
	$this.ket = other.ket;
};

BaseStemmer.copy_from$LBaseStemmer$LBaseStemmer$ = BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$;

BaseStemmer.prototype.in_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping$LBaseStemmer$AIII = BaseStemmer$in_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.in_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_grouping_b$LBaseStemmer$AIII = BaseStemmer$in_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0X1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping$LBaseStemmer$AIII = BaseStemmer$out_grouping$LBaseStemmer$AIII;

BaseStemmer.prototype.out_grouping_b$AIII = function (s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};


function BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, s, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	ch -= min;
	if ((s[ch >>> 3] & 0x1 << (ch & 0x7)) === 0) {
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		return true;
	}
	return false;
};

BaseStemmer.out_grouping_b$LBaseStemmer$AIII = BaseStemmer$out_grouping_b$LBaseStemmer$AIII;

BaseStemmer.prototype.in_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range$LBaseStemmer$II = BaseStemmer$in_range$LBaseStemmer$II;

BaseStemmer.prototype.in_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$in_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (ch > max || ch < min) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.in_range_b$LBaseStemmer$II = BaseStemmer$in_range_b$LBaseStemmer$II;

BaseStemmer.prototype.out_range$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor >= this.limit) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor >= $this.limit) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range$LBaseStemmer$II = BaseStemmer$out_range$LBaseStemmer$II;

BaseStemmer.prototype.out_range_b$II = function (min, max) {
	var ch;
	var $__jsx_postinc_t;
	if (this.cursor <= this.limit_backward) {
		return false;
	}
	ch = this.current.charCodeAt(this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};


function BaseStemmer$out_range_b$LBaseStemmer$II($this, min, max) {
	var ch;
	var $__jsx_postinc_t;
	if ($this.cursor <= $this.limit_backward) {
		return false;
	}
	ch = $this.current.charCodeAt($this.cursor - 1);
	if (! (ch > max || ch < min)) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	return true;
};

BaseStemmer.out_range_b$LBaseStemmer$II = BaseStemmer$out_range_b$LBaseStemmer$II;

BaseStemmer.prototype.eq_s$IS = function (s_size, s) {
	var cursor$0;
	if (((this.limit - this.cursor) | 0) < s_size) {
		return false;
	}
	if (this.current.slice(cursor$0 = this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	this.cursor = (this.cursor + s_size) | 0;
	return true;
};


function BaseStemmer$eq_s$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.limit - $this.cursor) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice(cursor$0 = $this.cursor, ((cursor$0 + s_size) | 0)) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor + s_size) | 0;
	return true;
};

BaseStemmer.eq_s$LBaseStemmer$IS = BaseStemmer$eq_s$LBaseStemmer$IS;

BaseStemmer.prototype.eq_s_b$IS = function (s_size, s) {
	var cursor$0;
	if (((this.cursor - this.limit_backward) | 0) < s_size) {
		return false;
	}
	if (this.current.slice((((cursor$0 = this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	this.cursor = (this.cursor - s_size) | 0;
	return true;
};


function BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s_size, s) {
	var cursor$0;
	if ((($this.cursor - $this.limit_backward) | 0) < s_size) {
		return false;
	}
	if ($this.current.slice((((cursor$0 = $this.cursor) - s_size) | 0), cursor$0) !== s) {
		return false;
	}
	$this.cursor = ($this.cursor - s_size) | 0;
	return true;
};

BaseStemmer.eq_s_b$LBaseStemmer$IS = BaseStemmer$eq_s_b$LBaseStemmer$IS;

BaseStemmer.prototype.eq_v$S = function (s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v$LBaseStemmer$S = BaseStemmer$eq_v$LBaseStemmer$S;

BaseStemmer.prototype.eq_v_b$S = function (s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS(this, s.length, s);
};


function BaseStemmer$eq_v_b$LBaseStemmer$S($this, s) {
	return BaseStemmer$eq_s_b$LBaseStemmer$IS($this, s.length, s);
};

BaseStemmer.eq_v_b$LBaseStemmer$S = BaseStemmer$eq_v_b$LBaseStemmer$S;

BaseStemmer.prototype.find_among$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	l = this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var l;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	l = $this.limit;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >>> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = common; i2 < w.s_size; i2++) {
			if (c + common === l) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c + common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c + w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(w.instance);
			$this.cursor = (c + w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among$LBaseStemmer$ALAmong$I = BaseStemmer$find_among$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.find_among_b$ALAmong$I = function (v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = this.cursor;
	lb = this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method(this);
			this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};


function BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, v, v_size) {
	var i;
	var j;
	var c;
	var lb;
	var common_i;
	var common_j;
	var first_key_inspected;
	var k;
	var diff;
	var common;
	var w;
	var i2;
	var res;
	i = 0;
	j = v_size;
	c = $this.cursor;
	lb = $this.limit_backward;
	common_i = 0;
	common_j = 0;
	first_key_inspected = false;
	while (true) {
		k = i + (j - i >> 1);
		diff = 0;
		common = (common_i < common_j ? common_i : common_j);
		w = v[k];
		for (i2 = w.s_size - 1 - common; i2 >= 0; i2--) {
			if (c - common === lb) {
				diff = -1;
				break;
			}
			diff = $this.current.charCodeAt(c - 1 - common) - w.s.charCodeAt(i2);
			if (diff !== 0) {
				break;
			}
			common++;
		}
		if (diff < 0) {
			j = k;
			common_j = common;
		} else {
			i = k;
			common_i = common;
		}
		if (j - i <= 1) {
			if (i > 0) {
				break;
			}
			if (j === i) {
				break;
			}
			if (first_key_inspected) {
				break;
			}
			first_key_inspected = true;
		}
	}
	while (true) {
		w = v[i];
		if (common_i >= w.s_size) {
			$this.cursor = (c - w.s_size | 0);
			if (w.method == null) {
				return w.result;
			}
			res = w.method($this);
			$this.cursor = (c - w.s_size | 0);
			if (res) {
				return w.result;
			}
		}
		i = w.substring_i;
		if (i < 0) {
			return 0;
		}
	}
	return -1;
};

BaseStemmer.find_among_b$LBaseStemmer$ALAmong$I = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I;

BaseStemmer.prototype.replace_s$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	this.current = this.current.slice(0, c_bra) + s + this.current.slice(c_ket);
	this.limit = (this.limit + adjustment) | 0;
	if (this.cursor >= c_ket) {
		this.cursor = (this.cursor + adjustment) | 0;
	} else if (this.cursor > c_bra) {
		this.cursor = c_bra;
	}
	return (adjustment | 0);
};


function BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = ((s.length - (((c_ket - c_bra) | 0))) | 0);
	$this.current = $this.current.slice(0, c_bra) + s + $this.current.slice(c_ket);
	$this.limit = ($this.limit + adjustment) | 0;
	if ($this.cursor >= c_ket) {
		$this.cursor = ($this.cursor + adjustment) | 0;
	} else if ($this.cursor > c_bra) {
		$this.cursor = c_bra;
	}
	return (adjustment | 0);
};

BaseStemmer.replace_s$LBaseStemmer$IIS = BaseStemmer$replace_s$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_check$ = function () {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true);
};


function BaseStemmer$slice_check$LBaseStemmer$($this) {
	var bra$0;
	var ket$0;
	var limit$0;
	return ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true);
};

BaseStemmer.slice_check$LBaseStemmer$ = BaseStemmer$slice_check$LBaseStemmer$;

BaseStemmer.prototype.slice_from$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS(this, this.bra, this.ket, s);
		result = true;
	}
	return result;
};


function BaseStemmer$slice_from$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = false;
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		BaseStemmer$replace_s$LBaseStemmer$IIS($this, $this.bra, $this.ket, s);
		result = true;
	}
	return result;
};

BaseStemmer.slice_from$LBaseStemmer$S = BaseStemmer$slice_from$LBaseStemmer$S;

BaseStemmer.prototype.slice_del$ = function () {
	return BaseStemmer$slice_from$LBaseStemmer$S(this, "");
};


function BaseStemmer$slice_del$LBaseStemmer$($this) {
	return BaseStemmer$slice_from$LBaseStemmer$S($this, "");
};

BaseStemmer.slice_del$LBaseStemmer$ = BaseStemmer$slice_del$LBaseStemmer$;

BaseStemmer.prototype.insert$IIS = function (c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS(this, c_bra, c_ket, s);
	if (c_bra <= this.bra) {
		this.bra = (this.bra + adjustment) | 0;
	}
	if (c_bra <= this.ket) {
		this.ket = (this.ket + adjustment) | 0;
	}
};


function BaseStemmer$insert$LBaseStemmer$IIS($this, c_bra, c_ket, s) {
	var adjustment;
	adjustment = BaseStemmer$replace_s$LBaseStemmer$IIS($this, c_bra, c_ket, s);
	if (c_bra <= $this.bra) {
		$this.bra = ($this.bra + adjustment) | 0;
	}
	if (c_bra <= $this.ket) {
		$this.ket = ($this.ket + adjustment) | 0;
	}
};

BaseStemmer.insert$LBaseStemmer$IIS = BaseStemmer$insert$LBaseStemmer$IIS;

BaseStemmer.prototype.slice_to$S = function (s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = this.bra) < 0 || bra$0 > (ket$0 = this.ket) || ket$0 > (limit$0 = this.limit) || limit$0 > this.current.length ? false : true) {
		result = this.current.slice(this.bra, this.ket);
	}
	return result;
};


function BaseStemmer$slice_to$LBaseStemmer$S($this, s) {
	var result;
	var bra$0;
	var ket$0;
	var limit$0;
	result = '';
	if ((bra$0 = $this.bra) < 0 || bra$0 > (ket$0 = $this.ket) || ket$0 > (limit$0 = $this.limit) || limit$0 > $this.current.length ? false : true) {
		result = $this.current.slice($this.bra, $this.ket);
	}
	return result;
};

BaseStemmer.slice_to$LBaseStemmer$S = BaseStemmer$slice_to$LBaseStemmer$S;

BaseStemmer.prototype.assign_to$S = function (s) {
	return this.current.slice(0, this.limit);
};


function BaseStemmer$assign_to$LBaseStemmer$S($this, s) {
	return $this.current.slice(0, $this.limit);
};

BaseStemmer.assign_to$LBaseStemmer$S = BaseStemmer$assign_to$LBaseStemmer$S;

BaseStemmer.prototype.stem$ = function () {
	return false;
};


BaseStemmer.prototype.stemWord$S = function (word) {
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	result = this.cache['.' + word];
	if (result == null) {
		current$0 = this.current = word;
		cursor$0 = this.cursor = 0;
		limit$0 = this.limit = current$0.length;
		this.limit_backward = 0;
		this.bra = cursor$0;
		this.ket = limit$0;
		this.stem$();
		result = this.current;
		this.cache['.' + word] = result;
	}
	return result;
};

BaseStemmer.prototype.stemWord = BaseStemmer.prototype.stemWord$S;

BaseStemmer.prototype.stemWords$AS = function (words) {
	var results;
	var i;
	var word;
	var result;
	var current$0;
	var cursor$0;
	var limit$0;
	results = [  ];
	for (i = 0; i < words.length; i++) {
		word = words[i];
		result = this.cache['.' + word];
		if (result == null) {
			current$0 = this.current = word;
			cursor$0 = this.cursor = 0;
			limit$0 = this.limit = current$0.length;
			this.limit_backward = 0;
			this.bra = cursor$0;
			this.ket = limit$0;
			this.stem$();
			result = this.current;
			this.cache['.' + word] = result;
		}
		results.push(result);
	}
	return results;
};

BaseStemmer.prototype.stemWords = BaseStemmer.prototype.stemWords$AS;

function FrenchStemmer() {
	BaseStemmer.call(this);
	this.I_p2 = 0;
	this.I_p1 = 0;
	this.I_pV = 0;
};

$__jsx_extend([FrenchStemmer], BaseStemmer);
FrenchStemmer.prototype.copy_from$LFrenchStemmer$ = function (other) {
	this.I_p2 = other.I_p2;
	this.I_p1 = other.I_p1;
	this.I_pV = other.I_pV;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

FrenchStemmer.prototype.copy_from = FrenchStemmer.prototype.copy_from$LFrenchStemmer$;

FrenchStemmer.prototype.r_prelude$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var cursor$0;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				v_2 = this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						v_3 = this.cursor;
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
								break lab5;
							}
							this.bra = this.cursor;
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								v_4 = this.cursor;
								lab7 = true;
							lab7:
								while (lab7 === true) {
									lab7 = false;
									if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "u")) {
										break lab7;
									}
									this.ket = this.cursor;
									if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
										break lab7;
									}
									if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "U")) {
										return false;
									}
									break lab6;
								}
								this.cursor = v_4;
								lab8 = true;
							lab8:
								while (lab8 === true) {
									lab8 = false;
									if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "i")) {
										break lab8;
									}
									this.ket = this.cursor;
									if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
										break lab8;
									}
									if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "I")) {
										return false;
									}
									break lab6;
								}
								this.cursor = v_4;
								if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "y")) {
									break lab5;
								}
								this.ket = this.cursor;
								if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "Y")) {
									return false;
								}
							}
							break lab4;
						}
						this.cursor = v_3;
						lab9 = true;
					lab9:
						while (lab9 === true) {
							lab9 = false;
							this.bra = this.cursor;
							if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "y")) {
								break lab9;
							}
							this.ket = this.cursor;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
								break lab9;
							}
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "Y")) {
								return false;
							}
							break lab4;
						}
						this.cursor = v_3;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "q")) {
							break lab3;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "u")) {
							break lab3;
						}
						this.ket = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "U")) {
							return false;
						}
					}
					this.cursor = v_2;
					break golab2;
				}
				cursor$0 = this.cursor = v_2;
				if (cursor$0 >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			continue replab0;
		}
		this.cursor = v_1;
		break replab0;
	}
	return true;
};

FrenchStemmer.prototype.r_prelude = FrenchStemmer.prototype.r_prelude$;

function FrenchStemmer$r_prelude$LFrenchStemmer$($this) {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var lab1;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var cursor$0;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
		golab2:
			while (true) {
				v_2 = $this.cursor;
				lab3 = true;
			lab3:
				while (lab3 === true) {
					lab3 = false;
					lab4 = true;
				lab4:
					while (lab4 === true) {
						lab4 = false;
						v_3 = $this.cursor;
						lab5 = true;
					lab5:
						while (lab5 === true) {
							lab5 = false;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
								break lab5;
							}
							$this.bra = $this.cursor;
							lab6 = true;
						lab6:
							while (lab6 === true) {
								lab6 = false;
								v_4 = $this.cursor;
								lab7 = true;
							lab7:
								while (lab7 === true) {
									lab7 = false;
									if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "u")) {
										break lab7;
									}
									$this.ket = $this.cursor;
									if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
										break lab7;
									}
									if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "U")) {
										return false;
									}
									break lab6;
								}
								$this.cursor = v_4;
								lab8 = true;
							lab8:
								while (lab8 === true) {
									lab8 = false;
									if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "i")) {
										break lab8;
									}
									$this.ket = $this.cursor;
									if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
										break lab8;
									}
									if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "I")) {
										return false;
									}
									break lab6;
								}
								$this.cursor = v_4;
								if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "y")) {
									break lab5;
								}
								$this.ket = $this.cursor;
								if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "Y")) {
									return false;
								}
							}
							break lab4;
						}
						$this.cursor = v_3;
						lab9 = true;
					lab9:
						while (lab9 === true) {
							lab9 = false;
							$this.bra = $this.cursor;
							if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "y")) {
								break lab9;
							}
							$this.ket = $this.cursor;
							if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
								break lab9;
							}
							if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "Y")) {
								return false;
							}
							break lab4;
						}
						$this.cursor = v_3;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "q")) {
							break lab3;
						}
						$this.bra = $this.cursor;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS($this, 1, "u")) {
							break lab3;
						}
						$this.ket = $this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "U")) {
							return false;
						}
					}
					$this.cursor = v_2;
					break golab2;
				}
				cursor$0 = $this.cursor = v_2;
				if (cursor$0 >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
			continue replab0;
		}
		$this.cursor = v_1;
		break replab0;
	}
	return true;
};

FrenchStemmer.r_prelude$LFrenchStemmer$ = FrenchStemmer$r_prelude$LFrenchStemmer$;

FrenchStemmer.prototype.r_mark_regions$ = function () {
	var v_1;
	var v_2;
	var v_4;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab8;
	var lab10;
	var lab12;
	var lab14;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var $__jsx_postinc_t;
	this.I_pV = limit$0 = this.limit;
	this.I_p1 = limit$0;
	this.I_p2 = limit$0;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = this.cursor;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab2;
				}
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab2;
				}
				if (this.cursor >= this.limit) {
					break lab2;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break lab1;
			}
			this.cursor = v_2;
			lab3 = true;
		lab3:
			while (lab3 === true) {
				lab3 = false;
				if (BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_0, 3) === 0) {
					break lab3;
				}
				break lab1;
			}
			cursor$0 = this.cursor = v_2;
			if (cursor$0 >= this.limit) {
				break lab0;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		golab4:
			while (true) {
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
						break lab5;
					}
					break golab4;
				}
				if (this.cursor >= this.limit) {
					break lab0;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
		}
		this.I_pV = this.cursor;
	}
	cursor$1 = this.cursor = v_1;
	v_4 = cursor$1;
	lab6 = true;
lab6:
	while (lab6 === true) {
		lab6 = false;
	golab7:
		while (true) {
			lab8 = true;
		lab8:
			while (lab8 === true) {
				lab8 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab8;
				}
				break golab7;
			}
			if (this.cursor >= this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab9:
		while (true) {
			lab10 = true;
		lab10:
			while (lab10 === true) {
				lab10 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab10;
				}
				break golab9;
			}
			if (this.cursor >= this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		this.I_p1 = this.cursor;
	golab11:
		while (true) {
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab12;
				}
				break golab11;
			}
			if (this.cursor >= this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab13:
		while (true) {
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
					break lab14;
				}
				break golab13;
			}
			if (this.cursor >= this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		this.I_p2 = this.cursor;
	}
	this.cursor = v_4;
	return true;
};

FrenchStemmer.prototype.r_mark_regions = FrenchStemmer.prototype.r_mark_regions$;

function FrenchStemmer$r_mark_regions$LFrenchStemmer$($this) {
	var v_1;
	var v_2;
	var v_4;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab5;
	var lab6;
	var lab8;
	var lab10;
	var lab12;
	var lab14;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var $__jsx_postinc_t;
	$this.I_pV = limit$0 = $this.limit;
	$this.I_p1 = limit$0;
	$this.I_p2 = limit$0;
	v_1 = $this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_2 = $this.cursor;
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab2;
				}
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab2;
				}
				if ($this.cursor >= $this.limit) {
					break lab2;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break lab1;
			}
			$this.cursor = v_2;
			lab3 = true;
		lab3:
			while (lab3 === true) {
				lab3 = false;
				if (BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_0, 3) === 0) {
					break lab3;
				}
				break lab1;
			}
			cursor$0 = $this.cursor = v_2;
			if (cursor$0 >= $this.limit) {
				break lab0;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		golab4:
			while (true) {
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
						break lab5;
					}
					break golab4;
				}
				if ($this.cursor >= $this.limit) {
					break lab0;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
			}
		}
		$this.I_pV = $this.cursor;
	}
	cursor$1 = $this.cursor = v_1;
	v_4 = cursor$1;
	lab6 = true;
lab6:
	while (lab6 === true) {
		lab6 = false;
	golab7:
		while (true) {
			lab8 = true;
		lab8:
			while (lab8 === true) {
				lab8 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab8;
				}
				break golab7;
			}
			if ($this.cursor >= $this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab9:
		while (true) {
			lab10 = true;
		lab10:
			while (lab10 === true) {
				lab10 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab10;
				}
				break golab9;
			}
			if ($this.cursor >= $this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		$this.I_p1 = $this.cursor;
	golab11:
		while (true) {
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab12;
				}
				break golab11;
			}
			if ($this.cursor >= $this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
	golab13:
		while (true) {
			lab14 = true;
		lab14:
			while (lab14 === true) {
				lab14 = false;
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
					break lab14;
				}
				break golab13;
			}
			if ($this.cursor >= $this.limit) {
				break lab6;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
		}
		$this.I_p2 = $this.cursor;
	}
	$this.cursor = v_4;
	return true;
};

FrenchStemmer.r_mark_regions$LFrenchStemmer$ = FrenchStemmer$r_mark_regions$LFrenchStemmer$;

FrenchStemmer.prototype.r_postlude$ = function () {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			this.bra = this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_1, 4);
			if (among_var === 0) {
				break lab1;
			}
			this.ket = this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "u")) {
					return false;
				}
				break;
			case 3:
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "y")) {
					return false;
				}
				break;
			case 4:
				if (this.cursor >= this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		this.cursor = v_1;
		break replab0;
	}
	return true;
};

FrenchStemmer.prototype.r_postlude = FrenchStemmer.prototype.r_postlude$;

function FrenchStemmer$r_postlude$LFrenchStemmer$($this) {
	var among_var;
	var v_1;
	var lab1;
	var $__jsx_postinc_t;
replab0:
	while (true) {
		v_1 = $this.cursor;
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			$this.bra = $this.cursor;
			among_var = BaseStemmer$find_among$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_1, 4);
			if (among_var === 0) {
				break lab1;
			}
			$this.ket = $this.cursor;
			switch (among_var) {
			case 0:
				break lab1;
			case 1:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
					return false;
				}
				break;
			case 2:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "u")) {
					return false;
				}
				break;
			case 3:
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "y")) {
					return false;
				}
				break;
			case 4:
				if ($this.cursor >= $this.limit) {
					break lab1;
				}
				($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				break;
			}
			continue replab0;
		}
		$this.cursor = v_1;
		break replab0;
	}
	return true;
};

FrenchStemmer.r_postlude$LFrenchStemmer$ = FrenchStemmer$r_postlude$LFrenchStemmer$;

FrenchStemmer.prototype.r_RV$ = function () {
	return (! (this.I_pV <= this.cursor) ? false : true);
};

FrenchStemmer.prototype.r_RV = FrenchStemmer.prototype.r_RV$;

function FrenchStemmer$r_RV$LFrenchStemmer$($this) {
	return (! ($this.I_pV <= $this.cursor) ? false : true);
};

FrenchStemmer.r_RV$LFrenchStemmer$ = FrenchStemmer$r_RV$LFrenchStemmer$;

FrenchStemmer.prototype.r_R1$ = function () {
	return (! (this.I_p1 <= this.cursor) ? false : true);
};

FrenchStemmer.prototype.r_R1 = FrenchStemmer.prototype.r_R1$;

function FrenchStemmer$r_R1$LFrenchStemmer$($this) {
	return (! ($this.I_p1 <= $this.cursor) ? false : true);
};

FrenchStemmer.r_R1$LFrenchStemmer$ = FrenchStemmer$r_R1$LFrenchStemmer$;

FrenchStemmer.prototype.r_R2$ = function () {
	return (! (this.I_p2 <= this.cursor) ? false : true);
};

FrenchStemmer.prototype.r_R2 = FrenchStemmer.prototype.r_R2$;

function FrenchStemmer$r_R2$LFrenchStemmer$($this) {
	return (! ($this.I_p2 <= $this.cursor) ? false : true);
};

FrenchStemmer.r_R2$LFrenchStemmer$ = FrenchStemmer$r_R2$LFrenchStemmer$;

FrenchStemmer.prototype.r_standard_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_4, 43);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_1 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			this.ket = this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ic")) {
				this.cursor = ((this.limit - v_1) | 0);
				break lab0;
			}
			this.bra = this.cursor;
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				v_2 = ((this.limit - this.cursor) | 0);
				lab2 = true;
			lab2:
				while (lab2 === true) {
					lab2 = false;
					if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
						break lab2;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					break lab1;
				}
				this.cursor = ((this.limit - v_2) | 0);
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "iqU")) {
					return false;
				}
			}
		}
		break;
	case 3:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "log")) {
			return false;
		}
		break;
	case 4:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "u")) {
			return false;
		}
		break;
	case 5:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ent")) {
			return false;
		}
		break;
	case 6:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_3 = ((this.limit - this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			this.ket = this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_2, 6);
			if (among_var === 0) {
				this.cursor = ((this.limit - v_3) | 0);
				break lab3;
			}
			this.bra = this.cursor;
			switch (among_var) {
			case 0:
				this.cursor = ((this.limit - v_3) | 0);
				break lab3;
			case 1:
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				this.ket = this.cursor;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "at")) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab3;
				}
				this.bra = cursor$0 = this.cursor;
				if (! (! (this.I_p2 <= cursor$0) ? false : true)) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			case 2:
				lab4 = true;
			lab4:
				while (lab4 === true) {
					lab4 = false;
					v_4 = ((this.limit - this.cursor) | 0);
					lab5 = true;
				lab5:
					while (lab5 === true) {
						lab5 = false;
						if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
							break lab5;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						break lab4;
					}
					cursor$1 = this.cursor = ((this.limit - v_4) | 0);
					if (! (! (this.I_p1 <= cursor$1) ? false : true)) {
						this.cursor = ((this.limit - v_3) | 0);
						break lab3;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "eux")) {
						return false;
					}
				}
				break;
			case 3:
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			case 4:
				if (! (! (this.I_pV <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
					return false;
				}
				break;
			}
		}
		break;
	case 7:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_5 = ((this.limit - this.cursor) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			this.ket = this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_3, 3);
			if (among_var === 0) {
				this.cursor = ((this.limit - v_5) | 0);
				break lab6;
			}
			this.bra = this.cursor;
			switch (among_var) {
			case 0:
				this.cursor = ((this.limit - v_5) | 0);
				break lab6;
			case 1:
				lab7 = true;
			lab7:
				while (lab7 === true) {
					lab7 = false;
					v_6 = ((this.limit - this.cursor) | 0);
					lab8 = true;
				lab8:
					while (lab8 === true) {
						lab8 = false;
						if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
							break lab8;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						break lab7;
					}
					this.cursor = ((this.limit - v_6) | 0);
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "abl")) {
						return false;
					}
				}
				break;
			case 2:
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					v_7 = ((this.limit - this.cursor) | 0);
					lab10 = true;
				lab10:
					while (lab10 === true) {
						lab10 = false;
						if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
							break lab10;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
							return false;
						}
						break lab9;
					}
					this.cursor = ((this.limit - v_7) | 0);
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "iqU")) {
						return false;
					}
				}
				break;
			case 3:
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					this.cursor = ((this.limit - v_5) | 0);
					break lab6;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 8:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_8 = ((this.limit - this.cursor) | 0);
		lab11 = true;
	lab11:
		while (lab11 === true) {
			lab11 = false;
			this.ket = this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "at")) {
				this.cursor = ((this.limit - v_8) | 0);
				break lab11;
			}
			this.bra = cursor$2 = this.cursor;
			if (! (! (this.I_p2 <= cursor$2) ? false : true)) {
				this.cursor = ((this.limit - v_8) | 0);
				break lab11;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			this.ket = this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "ic")) {
				this.cursor = ((this.limit - v_8) | 0);
				break lab11;
			}
			this.bra = this.cursor;
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				v_9 = ((this.limit - this.cursor) | 0);
				lab13 = true;
			lab13:
				while (lab13 === true) {
					lab13 = false;
					if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
						break lab13;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
						return false;
					}
					break lab12;
				}
				this.cursor = ((this.limit - v_9) | 0);
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "iqU")) {
					return false;
				}
			}
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "eau")) {
			return false;
		}
		break;
	case 10:
		if (! (! (this.I_p1 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "al")) {
			return false;
		}
		break;
	case 11:
		lab14 = true;
	lab14:
		while (lab14 === true) {
			lab14 = false;
			v_10 = ((this.limit - this.cursor) | 0);
			lab15 = true;
		lab15:
			while (lab15 === true) {
				lab15 = false;
				if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
					break lab15;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
					return false;
				}
				break lab14;
			}
			cursor$3 = this.cursor = ((this.limit - v_10) | 0);
			if (! (! (this.I_p1 <= cursor$3) ? false : true)) {
				return false;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "eux")) {
				return false;
			}
		}
		break;
	case 12:
		if (! (! (this.I_p1 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 13:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ant")) {
			return false;
		}
		return false;
	case 14:
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ent")) {
			return false;
		}
		return false;
	case 15:
		v_11 = ((this.limit - this.cursor) | 0);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
			return false;
		}
		if (! (! (this.I_pV <= this.cursor) ? false : true)) {
			return false;
		}
		this.cursor = ((this.limit - v_11) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		return false;
	}
	return true;
};

FrenchStemmer.prototype.r_standard_suffix = FrenchStemmer.prototype.r_standard_suffix$;

function FrenchStemmer$r_standard_suffix$LFrenchStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_10;
	var v_11;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var lab14;
	var lab15;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_4, 43);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_1 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			$this.ket = $this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ic")) {
				$this.cursor = (($this.limit - v_1) | 0);
				break lab0;
			}
			$this.bra = $this.cursor;
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				v_2 = (($this.limit - $this.cursor) | 0);
				lab2 = true;
			lab2:
				while (lab2 === true) {
					lab2 = false;
					if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
						break lab2;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					break lab1;
				}
				$this.cursor = (($this.limit - v_2) | 0);
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "iqU")) {
					return false;
				}
			}
		}
		break;
	case 3:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "log")) {
			return false;
		}
		break;
	case 4:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "u")) {
			return false;
		}
		break;
	case 5:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ent")) {
			return false;
		}
		break;
	case 6:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_3 = (($this.limit - $this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			$this.ket = $this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_2, 6);
			if (among_var === 0) {
				$this.cursor = (($this.limit - v_3) | 0);
				break lab3;
			}
			$this.bra = $this.cursor;
			switch (among_var) {
			case 0:
				$this.cursor = (($this.limit - v_3) | 0);
				break lab3;
			case 1:
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				$this.ket = $this.cursor;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "at")) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab3;
				}
				$this.bra = cursor$0 = $this.cursor;
				if (! (! ($this.I_p2 <= cursor$0) ? false : true)) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			case 2:
				lab4 = true;
			lab4:
				while (lab4 === true) {
					lab4 = false;
					v_4 = (($this.limit - $this.cursor) | 0);
					lab5 = true;
				lab5:
					while (lab5 === true) {
						lab5 = false;
						if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
							break lab5;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						break lab4;
					}
					cursor$1 = $this.cursor = (($this.limit - v_4) | 0);
					if (! (! ($this.I_p1 <= cursor$1) ? false : true)) {
						$this.cursor = (($this.limit - v_3) | 0);
						break lab3;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "eux")) {
						return false;
					}
				}
				break;
			case 3:
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			case 4:
				if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_3) | 0);
					break lab3;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
					return false;
				}
				break;
			}
		}
		break;
	case 7:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_5 = (($this.limit - $this.cursor) | 0);
		lab6 = true;
	lab6:
		while (lab6 === true) {
			lab6 = false;
			$this.ket = $this.cursor;
			among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_3, 3);
			if (among_var === 0) {
				$this.cursor = (($this.limit - v_5) | 0);
				break lab6;
			}
			$this.bra = $this.cursor;
			switch (among_var) {
			case 0:
				$this.cursor = (($this.limit - v_5) | 0);
				break lab6;
			case 1:
				lab7 = true;
			lab7:
				while (lab7 === true) {
					lab7 = false;
					v_6 = (($this.limit - $this.cursor) | 0);
					lab8 = true;
				lab8:
					while (lab8 === true) {
						lab8 = false;
						if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
							break lab8;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						break lab7;
					}
					$this.cursor = (($this.limit - v_6) | 0);
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "abl")) {
						return false;
					}
				}
				break;
			case 2:
				lab9 = true;
			lab9:
				while (lab9 === true) {
					lab9 = false;
					v_7 = (($this.limit - $this.cursor) | 0);
					lab10 = true;
				lab10:
					while (lab10 === true) {
						lab10 = false;
						if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
							break lab10;
						}
						if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
							return false;
						}
						break lab9;
					}
					$this.cursor = (($this.limit - v_7) | 0);
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "iqU")) {
						return false;
					}
				}
				break;
			case 3:
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					$this.cursor = (($this.limit - v_5) | 0);
					break lab6;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break;
			}
		}
		break;
	case 8:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_8 = (($this.limit - $this.cursor) | 0);
		lab11 = true;
	lab11:
		while (lab11 === true) {
			lab11 = false;
			$this.ket = $this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "at")) {
				$this.cursor = (($this.limit - v_8) | 0);
				break lab11;
			}
			$this.bra = cursor$2 = $this.cursor;
			if (! (! ($this.I_p2 <= cursor$2) ? false : true)) {
				$this.cursor = (($this.limit - v_8) | 0);
				break lab11;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			$this.ket = $this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "ic")) {
				$this.cursor = (($this.limit - v_8) | 0);
				break lab11;
			}
			$this.bra = $this.cursor;
			lab12 = true;
		lab12:
			while (lab12 === true) {
				lab12 = false;
				v_9 = (($this.limit - $this.cursor) | 0);
				lab13 = true;
			lab13:
				while (lab13 === true) {
					lab13 = false;
					if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
						break lab13;
					}
					if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
						return false;
					}
					break lab12;
				}
				$this.cursor = (($this.limit - v_9) | 0);
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "iqU")) {
					return false;
				}
			}
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "eau")) {
			return false;
		}
		break;
	case 10:
		if (! (! ($this.I_p1 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "al")) {
			return false;
		}
		break;
	case 11:
		lab14 = true;
	lab14:
		while (lab14 === true) {
			lab14 = false;
			v_10 = (($this.limit - $this.cursor) | 0);
			lab15 = true;
		lab15:
			while (lab15 === true) {
				lab15 = false;
				if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
					break lab15;
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
					return false;
				}
				break lab14;
			}
			cursor$3 = $this.cursor = (($this.limit - v_10) | 0);
			if (! (! ($this.I_p1 <= cursor$3) ? false : true)) {
				return false;
			}
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "eux")) {
				return false;
			}
		}
		break;
	case 12:
		if (! (! ($this.I_p1 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 13:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ant")) {
			return false;
		}
		return false;
	case 14:
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ent")) {
			return false;
		}
		return false;
	case 15:
		v_11 = (($this.limit - $this.cursor) | 0);
		if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
			return false;
		}
		if (! (! ($this.I_pV <= $this.cursor) ? false : true)) {
			return false;
		}
		$this.cursor = (($this.limit - v_11) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		return false;
	}
	return true;
};

FrenchStemmer.r_standard_suffix$LFrenchStemmer$ = FrenchStemmer$r_standard_suffix$LFrenchStemmer$;

FrenchStemmer.prototype.r_i_verb_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_pV) {
		return false;
	}
	cursor$1 = this.cursor = this.I_pV;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_5, 35);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		this.limit_backward = v_2;
		return false;
	case 1:
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
			this.limit_backward = v_2;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	this.limit_backward = v_2;
	return true;
};

FrenchStemmer.prototype.r_i_verb_suffix = FrenchStemmer.prototype.r_i_verb_suffix$;

function FrenchStemmer$r_i_verb_suffix$LFrenchStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_pV) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_pV;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_5, 35);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		$this.limit_backward = v_2;
		return false;
	case 1:
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
			$this.limit_backward = v_2;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	$this.limit_backward = v_2;
	return true;
};

FrenchStemmer.r_i_verb_suffix$LFrenchStemmer$ = FrenchStemmer$r_i_verb_suffix$LFrenchStemmer$;

FrenchStemmer.prototype.r_verb_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = ((this.limit - (cursor$0 = this.cursor)) | 0);
	if (cursor$0 < this.I_pV) {
		return false;
	}
	cursor$1 = this.cursor = this.I_pV;
	v_2 = this.limit_backward;
	this.limit_backward = cursor$1;
	cursor$2 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_6, 38);
	if (among_var === 0) {
		this.limit_backward = v_2;
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		this.limit_backward = v_2;
		return false;
	case 1:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			this.limit_backward = v_2;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_3 = ((this.limit - this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			this.ket = this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
				this.cursor = ((this.limit - v_3) | 0);
				break lab0;
			}
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
		}
		break;
	}
	this.limit_backward = v_2;
	return true;
};

FrenchStemmer.prototype.r_verb_suffix = FrenchStemmer.prototype.r_verb_suffix$;

function FrenchStemmer$r_verb_suffix$LFrenchStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var lab0;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	v_1 = (($this.limit - (cursor$0 = $this.cursor)) | 0);
	if (cursor$0 < $this.I_pV) {
		return false;
	}
	cursor$1 = $this.cursor = $this.I_pV;
	v_2 = $this.limit_backward;
	$this.limit_backward = cursor$1;
	cursor$2 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$2;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_6, 38);
	if (among_var === 0) {
		$this.limit_backward = v_2;
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		$this.limit_backward = v_2;
		return false;
	case 1:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			$this.limit_backward = v_2;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_3 = (($this.limit - $this.cursor) | 0);
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			$this.ket = $this.cursor;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
				$this.cursor = (($this.limit - v_3) | 0);
				break lab0;
			}
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
		}
		break;
	}
	$this.limit_backward = v_2;
	return true;
};

FrenchStemmer.r_verb_suffix$LFrenchStemmer$ = FrenchStemmer$r_verb_suffix$LFrenchStemmer$;

FrenchStemmer.prototype.r_residual_suffix$ = function () {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	v_1 = ((this.limit - this.cursor) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		this.ket = this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "s")) {
			this.cursor = ((this.limit - v_1) | 0);
			break lab0;
		}
		this.bra = cursor$0 = this.cursor;
		v_2 = ((this.limit - cursor$0) | 0);
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FrenchStemmer.g_keep_with_s, 97, 232)) {
			this.cursor = ((this.limit - v_1) | 0);
			break lab0;
		}
		this.cursor = ((this.limit - v_2) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
	}
	v_3 = ((this.limit - (cursor$1 = this.cursor)) | 0);
	if (cursor$1 < this.I_pV) {
		return false;
	}
	cursor$2 = this.cursor = this.I_pV;
	v_4 = this.limit_backward;
	this.limit_backward = cursor$2;
	cursor$3 = this.cursor = ((this.limit - v_3) | 0);
	this.ket = cursor$3;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_7, 7);
	if (among_var === 0) {
		this.limit_backward = v_4;
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		this.limit_backward = v_4;
		return false;
	case 1:
		if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
			this.limit_backward = v_4;
			return false;
		}
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_5 = ((this.limit - this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "s")) {
					break lab2;
				}
				break lab1;
			}
			this.cursor = ((this.limit - v_5) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "t")) {
				this.limit_backward = v_4;
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 2, "gu")) {
			this.limit_backward = v_4;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	this.limit_backward = v_4;
	return true;
};

FrenchStemmer.prototype.r_residual_suffix = FrenchStemmer.prototype.r_residual_suffix$;

function FrenchStemmer$r_residual_suffix$LFrenchStemmer$($this) {
	var among_var;
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var cursor$3;
	v_1 = (($this.limit - $this.cursor) | 0);
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		$this.ket = $this.cursor;
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "s")) {
			$this.cursor = (($this.limit - v_1) | 0);
			break lab0;
		}
		$this.bra = cursor$0 = $this.cursor;
		v_2 = (($this.limit - cursor$0) | 0);
		if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FrenchStemmer.g_keep_with_s, 97, 232)) {
			$this.cursor = (($this.limit - v_1) | 0);
			break lab0;
		}
		$this.cursor = (($this.limit - v_2) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
	}
	v_3 = (($this.limit - (cursor$1 = $this.cursor)) | 0);
	if (cursor$1 < $this.I_pV) {
		return false;
	}
	cursor$2 = $this.cursor = $this.I_pV;
	v_4 = $this.limit_backward;
	$this.limit_backward = cursor$2;
	cursor$3 = $this.cursor = (($this.limit - v_3) | 0);
	$this.ket = cursor$3;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_7, 7);
	if (among_var === 0) {
		$this.limit_backward = v_4;
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		$this.limit_backward = v_4;
		return false;
	case 1:
		if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
			$this.limit_backward = v_4;
			return false;
		}
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			v_5 = (($this.limit - $this.cursor) | 0);
			lab2 = true;
		lab2:
			while (lab2 === true) {
				lab2 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "s")) {
					break lab2;
				}
				break lab1;
			}
			$this.cursor = (($this.limit - v_5) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "t")) {
				$this.limit_backward = v_4;
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 2, "gu")) {
			$this.limit_backward = v_4;
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	$this.limit_backward = v_4;
	return true;
};

FrenchStemmer.r_residual_suffix$LFrenchStemmer$ = FrenchStemmer$r_residual_suffix$LFrenchStemmer$;

FrenchStemmer.prototype.r_un_double$ = function () {
	var v_1;
	var cursor$0;
	var $__jsx_postinc_t;
	v_1 = ((this.limit - this.cursor) | 0);
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, FrenchStemmer.a_8, 5) === 0) {
		return false;
	}
	cursor$0 = this.cursor = ((this.limit - v_1) | 0);
	this.ket = cursor$0;
	if (cursor$0 <= this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	this.bra = this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

FrenchStemmer.prototype.r_un_double = FrenchStemmer.prototype.r_un_double$;

function FrenchStemmer$r_un_double$LFrenchStemmer$($this) {
	var v_1;
	var cursor$0;
	var $__jsx_postinc_t;
	v_1 = (($this.limit - $this.cursor) | 0);
	if (BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, FrenchStemmer.a_8, 5) === 0) {
		return false;
	}
	cursor$0 = $this.cursor = (($this.limit - v_1) | 0);
	$this.ket = cursor$0;
	if (cursor$0 <= $this.limit_backward) {
		return false;
	}
	($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	$this.bra = $this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

FrenchStemmer.r_un_double$LFrenchStemmer$ = FrenchStemmer$r_un_double$LFrenchStemmer$;

FrenchStemmer.prototype.r_un_accent$ = function () {
	var v_3;
	var v_1;
	var lab1;
	var lab2;
	var lab3;
	v_1 = 1;
replab0:
	while (true) {
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, FrenchStemmer.g_v, 97, 251)) {
				break lab1;
			}
			v_1--;
			continue replab0;
		}
		break replab0;
	}
	if (v_1 > 0) {
		return false;
	}
	this.ket = this.cursor;
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = ((this.limit - this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00E9")) {
				break lab3;
			}
			break lab2;
		}
		this.cursor = ((this.limit - v_3) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00E8")) {
			return false;
		}
	}
	this.bra = this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e") ? false : true);
};

FrenchStemmer.prototype.r_un_accent = FrenchStemmer.prototype.r_un_accent$;

function FrenchStemmer$r_un_accent$LFrenchStemmer$($this) {
	var v_3;
	var v_1;
	var lab1;
	var lab2;
	var lab3;
	v_1 = 1;
replab0:
	while (true) {
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, FrenchStemmer.g_v, 97, 251)) {
				break lab1;
			}
			v_1--;
			continue replab0;
		}
		break replab0;
	}
	if (v_1 > 0) {
		return false;
	}
	$this.ket = $this.cursor;
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		v_3 = (($this.limit - $this.cursor) | 0);
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00E9")) {
				break lab3;
			}
			break lab2;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "\u00E8")) {
			return false;
		}
	}
	$this.bra = $this.cursor;
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e") ? false : true);
};

FrenchStemmer.r_un_accent$LFrenchStemmer$ = FrenchStemmer$r_un_accent$LFrenchStemmer$;

FrenchStemmer.prototype.stem$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_6;
	var v_7;
	var v_8;
	var v_9;
	var v_11;
	var lab0;
	var lab1;
	var lab2;
	var lab3;
	var lab4;
	var lab5;
	var lab6;
	var lab7;
	var lab8;
	var lab9;
	var lab10;
	var lab11;
	var lab12;
	var lab13;
	var cursor$0;
	var limit$0;
	var cursor$1;
	var cursor$2;
	var limit$1;
	var cursor$3;
	var limit$2;
	var cursor$4;
	var cursor$5;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		if (! FrenchStemmer$r_prelude$LFrenchStemmer$(this)) {
			break lab0;
		}
	}
	cursor$0 = this.cursor = v_1;
	v_2 = cursor$0;
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
		if (! FrenchStemmer$r_mark_regions$LFrenchStemmer$(this)) {
			break lab1;
		}
	}
	cursor$2 = this.cursor = v_2;
	this.limit_backward = cursor$2;
	cursor$3 = this.cursor = limit$1 = this.limit;
	v_3 = ((limit$1 - cursor$3) | 0);
	lab2 = true;
lab2:
	while (lab2 === true) {
		lab2 = false;
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			v_4 = ((this.limit - this.cursor) | 0);
			lab4 = true;
		lab4:
			while (lab4 === true) {
				lab4 = false;
				v_5 = ((this.limit - this.cursor) | 0);
				lab5 = true;
			lab5:
				while (lab5 === true) {
					lab5 = false;
					v_6 = ((this.limit - this.cursor) | 0);
					lab6 = true;
				lab6:
					while (lab6 === true) {
						lab6 = false;
						if (! FrenchStemmer$r_standard_suffix$LFrenchStemmer$(this)) {
							break lab6;
						}
						break lab5;
					}
					this.cursor = ((this.limit - v_6) | 0);
					lab7 = true;
				lab7:
					while (lab7 === true) {
						lab7 = false;
						if (! FrenchStemmer$r_i_verb_suffix$LFrenchStemmer$(this)) {
							break lab7;
						}
						break lab5;
					}
					this.cursor = ((this.limit - v_6) | 0);
					if (! FrenchStemmer$r_verb_suffix$LFrenchStemmer$(this)) {
						break lab4;
					}
				}
				cursor$1 = this.cursor = (((limit$0 = this.limit) - v_5) | 0);
				v_7 = ((limit$0 - cursor$1) | 0);
				lab8 = true;
			lab8:
				while (lab8 === true) {
					lab8 = false;
					this.ket = this.cursor;
					lab9 = true;
				lab9:
					while (lab9 === true) {
						lab9 = false;
						v_8 = ((this.limit - this.cursor) | 0);
						lab10 = true;
					lab10:
						while (lab10 === true) {
							lab10 = false;
							if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "Y")) {
								break lab10;
							}
							this.bra = this.cursor;
							if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i")) {
								return false;
							}
							break lab9;
						}
						this.cursor = ((this.limit - v_8) | 0);
						if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "\u00E7")) {
							this.cursor = ((this.limit - v_7) | 0);
							break lab8;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "c")) {
							return false;
						}
					}
				}
				break lab3;
			}
			this.cursor = ((this.limit - v_4) | 0);
			if (! FrenchStemmer$r_residual_suffix$LFrenchStemmer$(this)) {
				break lab2;
			}
		}
	}
	cursor$4 = this.cursor = (((limit$2 = this.limit) - v_3) | 0);
	v_9 = ((limit$2 - cursor$4) | 0);
	lab11 = true;
lab11:
	while (lab11 === true) {
		lab11 = false;
		if (! FrenchStemmer$r_un_double$LFrenchStemmer$(this)) {
			break lab11;
		}
	}
	this.cursor = ((this.limit - v_9) | 0);
	lab12 = true;
lab12:
	while (lab12 === true) {
		lab12 = false;
		if (! FrenchStemmer$r_un_accent$LFrenchStemmer$(this)) {
			break lab12;
		}
	}
	cursor$5 = this.cursor = this.limit_backward;
	v_11 = cursor$5;
	lab13 = true;
lab13:
	while (lab13 === true) {
		lab13 = false;
		if (! FrenchStemmer$r_postlude$LFrenchStemmer$(this)) {
			break lab13;
		}
	}
	this.cursor = v_11;
	return true;
};

FrenchStemmer.prototype.stem = FrenchStemmer.prototype.stem$;

FrenchStemmer.prototype.equals$X = function (o) {
	return o instanceof FrenchStemmer;
};

FrenchStemmer.prototype.equals = FrenchStemmer.prototype.equals$X;

function FrenchStemmer$equals$LFrenchStemmer$X($this, o) {
	return o instanceof FrenchStemmer;
};

FrenchStemmer.equals$LFrenchStemmer$X = FrenchStemmer$equals$LFrenchStemmer$X;

FrenchStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "FrenchStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

FrenchStemmer.prototype.hashCode = FrenchStemmer.prototype.hashCode$;

function FrenchStemmer$hashCode$LFrenchStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "FrenchStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

FrenchStemmer.hashCode$LFrenchStemmer$ = FrenchStemmer$hashCode$LFrenchStemmer$;

FrenchStemmer.serialVersionUID = 1;
$__jsx_lazy_init(FrenchStemmer, "methodObject", function () {
	return new FrenchStemmer();
});
$__jsx_lazy_init(FrenchStemmer, "a_0", function () {
	return [ new Among("col", -1, -1), new Among("par", -1, -1), new Among("tap", -1, -1) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_1", function () {
	return [ new Among("", -1, 4), new Among("I", 0, 1), new Among("U", 0, 2), new Among("Y", 0, 3) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_2", function () {
	return [ new Among("iqU", -1, 3), new Among("abl", -1, 3), new Among("I\u00E8r", -1, 4), new Among("i\u00E8r", -1, 4), new Among("eus", -1, 2), new Among("iv", -1, 1) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_3", function () {
	return [ new Among("ic", -1, 2), new Among("abil", -1, 1), new Among("iv", -1, 3) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_4", function () {
	return [ new Among("iqUe", -1, 1), new Among("atrice", -1, 2), new Among("ance", -1, 1), new Among("ence", -1, 5), new Among("logie", -1, 3), new Among("able", -1, 1), new Among("isme", -1, 1), new Among("euse", -1, 11), new Among("iste", -1, 1), new Among("ive", -1, 8), new Among("if", -1, 8), new Among("usion", -1, 4), new Among("ation", -1, 2), new Among("ution", -1, 4), new Among("ateur", -1, 2), new Among("iqUes", -1, 1), new Among("atrices", -1, 2), new Among("ances", -1, 1), new Among("ences", -1, 5), new Among("logies", -1, 3), new Among("ables", -1, 1), new Among("ismes", -1, 1), new Among("euses", -1, 11), new Among("istes", -1, 1), new Among("ives", -1, 8), new Among("ifs", -1, 8), new Among("usions", -1, 4), new Among("ations", -1, 2), new Among("utions", -1, 4), new Among("ateurs", -1, 2), new Among("ments", -1, 15), new Among("ements", 30, 6), new Among("issements", 31, 12), new Among("it\u00E9s", -1, 7), new Among("ment", -1, 15), new Among("ement", 34, 6), new Among("issement", 35, 12), new Among("amment", 34, 13), new Among("emment", 34, 14), new Among("aux", -1, 10), new Among("eaux", 39, 9), new Among("eux", -1, 1), new Among("it\u00E9", -1, 7) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_5", function () {
	return [ new Among("ira", -1, 1), new Among("ie", -1, 1), new Among("isse", -1, 1), new Among("issante", -1, 1), new Among("i", -1, 1), new Among("irai", 4, 1), new Among("ir", -1, 1), new Among("iras", -1, 1), new Among("ies", -1, 1), new Among("\u00EEmes", -1, 1), new Among("isses", -1, 1), new Among("issantes", -1, 1), new Among("\u00EEtes", -1, 1), new Among("is", -1, 1), new Among("irais", 13, 1), new Among("issais", 13, 1), new Among("irions", -1, 1), new Among("issions", -1, 1), new Among("irons", -1, 1), new Among("issons", -1, 1), new Among("issants", -1, 1), new Among("it", -1, 1), new Among("irait", 21, 1), new Among("issait", 21, 1), new Among("issant", -1, 1), new Among("iraIent", -1, 1), new Among("issaIent", -1, 1), new Among("irent", -1, 1), new Among("issent", -1, 1), new Among("iront", -1, 1), new Among("\u00EEt", -1, 1), new Among("iriez", -1, 1), new Among("issiez", -1, 1), new Among("irez", -1, 1), new Among("issez", -1, 1) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_6", function () {
	return [ new Among("a", -1, 3), new Among("era", 0, 2), new Among("asse", -1, 3), new Among("ante", -1, 3), new Among("\u00E9e", -1, 2), new Among("ai", -1, 3), new Among("erai", 5, 2), new Among("er", -1, 2), new Among("as", -1, 3), new Among("eras", 8, 2), new Among("\u00E2mes", -1, 3), new Among("asses", -1, 3), new Among("antes", -1, 3), new Among("\u00E2tes", -1, 3), new Among("\u00E9es", -1, 2), new Among("ais", -1, 3), new Among("erais", 15, 2), new Among("ions", -1, 1), new Among("erions", 17, 2), new Among("assions", 17, 3), new Among("erons", -1, 2), new Among("ants", -1, 3), new Among("\u00E9s", -1, 2), new Among("ait", -1, 3), new Among("erait", 23, 2), new Among("ant", -1, 3), new Among("aIent", -1, 3), new Among("eraIent", 26, 2), new Among("\u00E8rent", -1, 2), new Among("assent", -1, 3), new Among("eront", -1, 2), new Among("\u00E2t", -1, 3), new Among("ez", -1, 2), new Among("iez", 32, 2), new Among("eriez", 33, 2), new Among("assiez", 33, 3), new Among("erez", 32, 2), new Among("\u00E9", -1, 2) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_7", function () {
	return [ new Among("e", -1, 3), new Among("I\u00E8re", 0, 2), new Among("i\u00E8re", 0, 2), new Among("ion", -1, 1), new Among("Ier", -1, 2), new Among("ier", -1, 2), new Among("\u00EB", -1, 4) ];
});
$__jsx_lazy_init(FrenchStemmer, "a_8", function () {
	return [ new Among("ell", -1, -1), new Among("eill", -1, -1), new Among("enn", -1, -1), new Among("onn", -1, -1), new Among("ett", -1, -1) ];
});
FrenchStemmer.g_v = [ 17, 65, 16, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128, 130, 103, 8, 5 ];
FrenchStemmer.g_keep_with_s = [ 1, 65, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 128 ];

var $__jsx_classMap = {
	"src/among.jsx": {
		Among: Among,
		Among$SII: Among,
		Among$SIIF$LBaseStemmer$B$LBaseStemmer$: Among$0
	},
	"src/stemmer.jsx": {
		Stemmer: Stemmer,
		Stemmer$: Stemmer
	},
	"src/base-stemmer.jsx": {
		BaseStemmer: BaseStemmer,
		BaseStemmer$: BaseStemmer
	},
	"src/french-stemmer.jsx": {
		FrenchStemmer: FrenchStemmer,
		FrenchStemmer$: FrenchStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var FrenchStemmer = JSX.require("src/french-stemmer.jsx").FrenchStemmer;
