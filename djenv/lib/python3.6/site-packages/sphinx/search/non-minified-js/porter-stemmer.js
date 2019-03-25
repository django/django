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

function PorterStemmer() {
	BaseStemmer.call(this);
	this.B_Y_found = false;
	this.I_p2 = 0;
	this.I_p1 = 0;
};

$__jsx_extend([PorterStemmer], BaseStemmer);
PorterStemmer.prototype.copy_from$LPorterStemmer$ = function (other) {
	this.B_Y_found = other.B_Y_found;
	this.I_p2 = other.I_p2;
	this.I_p1 = other.I_p1;
	BaseStemmer$copy_from$LBaseStemmer$LBaseStemmer$(this, other);
};

PorterStemmer.prototype.copy_from = PorterStemmer.prototype.copy_from$LPorterStemmer$;

PorterStemmer.prototype.r_shortv$ = function () {
	return (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, PorterStemmer.g_v_WXY, 89, 121) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121) ? false : ! BaseStemmer$out_grouping_b$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121) ? false : true);
};

PorterStemmer.prototype.r_shortv = PorterStemmer.prototype.r_shortv$;

function PorterStemmer$r_shortv$LPorterStemmer$($this) {
	return (! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, PorterStemmer.g_v_WXY, 89, 121) ? false : ! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, PorterStemmer.g_v, 97, 121) ? false : ! BaseStemmer$out_grouping_b$LBaseStemmer$AIII($this, PorterStemmer.g_v, 97, 121) ? false : true);
};

PorterStemmer.r_shortv$LPorterStemmer$ = PorterStemmer$r_shortv$LPorterStemmer$;

PorterStemmer.prototype.r_R1$ = function () {
	return (! (this.I_p1 <= this.cursor) ? false : true);
};

PorterStemmer.prototype.r_R1 = PorterStemmer.prototype.r_R1$;

function PorterStemmer$r_R1$LPorterStemmer$($this) {
	return (! ($this.I_p1 <= $this.cursor) ? false : true);
};

PorterStemmer.r_R1$LPorterStemmer$ = PorterStemmer$r_R1$LPorterStemmer$;

PorterStemmer.prototype.r_R2$ = function () {
	return (! (this.I_p2 <= this.cursor) ? false : true);
};

PorterStemmer.prototype.r_R2 = PorterStemmer.prototype.r_R2$;

function PorterStemmer$r_R2$LPorterStemmer$($this) {
	return (! ($this.I_p2 <= $this.cursor) ? false : true);
};

PorterStemmer.r_R2$LPorterStemmer$ = PorterStemmer$r_R2$LPorterStemmer$;

PorterStemmer.prototype.r_Step_1a$ = function () {
	var among_var;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_0, 4);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ss")) {
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
	}
	return true;
};

PorterStemmer.prototype.r_Step_1a = PorterStemmer.prototype.r_Step_1a$;

function PorterStemmer$r_Step_1a$LPorterStemmer$($this) {
	var among_var;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_0, 4);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ss")) {
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
	}
	return true;
};

PorterStemmer.r_Step_1a$LPorterStemmer$ = PorterStemmer$r_Step_1a$LPorterStemmer$;

PorterStemmer.prototype.r_Step_1b$ = function () {
	var among_var;
	var v_1;
	var v_3;
	var v_4;
	var lab1;
	var c;
	var c_bra$0;
	var adjustment$0;
	var c_bra$1;
	var adjustment$1;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var $__jsx_postinc_t;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_2, 3);
	if (among_var === 0) {
		return false;
	}
	this.bra = this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! (this.I_p1 <= this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ee")) {
			return false;
		}
		break;
	case 2:
		v_1 = ((this.limit - this.cursor) | 0);
	golab0:
		while (true) {
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
					break lab1;
				}
				break golab0;
			}
			if (this.cursor <= this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
		this.cursor = ((this.limit - v_1) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		v_3 = ((this.limit - this.cursor) | 0);
		among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_1, 13);
		if (among_var === 0) {
			return false;
		}
		this.cursor = ((this.limit - v_3) | 0);
		switch (among_var) {
		case 0:
			return false;
		case 1:
			c = cursor$0 = this.cursor;
			c_bra$0 = cursor$0;
			adjustment$0 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$0, cursor$0, "e");
			if (cursor$0 <= this.bra) {
				this.bra = (this.bra + adjustment$0) | 0;
			}
			if (c_bra$0 <= this.ket) {
				this.ket = (this.ket + adjustment$0) | 0;
			}
			this.cursor = c;
			break;
		case 2:
			this.ket = cursor$1 = this.cursor;
			if (cursor$1 <= this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			this.bra = this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
				return false;
			}
			break;
		case 3:
			if (this.cursor !== this.I_p1) {
				return false;
			}
			v_4 = ((this.limit - this.cursor) | 0);
			if (! PorterStemmer$r_shortv$LPorterStemmer$(this)) {
				return false;
			}
			cursor$2 = this.cursor = ((this.limit - v_4) | 0);
			c = cursor$2;
			c_bra$1 = cursor$2;
			adjustment$1 = BaseStemmer$replace_s$LBaseStemmer$IIS(this, cursor$2, cursor$2, "e");
			if (cursor$2 <= this.bra) {
				this.bra = (this.bra + adjustment$1) | 0;
			}
			if (c_bra$1 <= this.ket) {
				this.ket = (this.ket + adjustment$1) | 0;
			}
			this.cursor = c;
			break;
		}
		break;
	}
	return true;
};

PorterStemmer.prototype.r_Step_1b = PorterStemmer.prototype.r_Step_1b$;

function PorterStemmer$r_Step_1b$LPorterStemmer$($this) {
	var among_var;
	var v_1;
	var v_3;
	var v_4;
	var lab1;
	var c;
	var c_bra$0;
	var adjustment$0;
	var c_bra$1;
	var adjustment$1;
	var cursor$0;
	var cursor$1;
	var cursor$2;
	var $__jsx_postinc_t;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_2, 3);
	if (among_var === 0) {
		return false;
	}
	$this.bra = $this.cursor;
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! (! ($this.I_p1 <= $this.cursor) ? false : true)) {
			return false;
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ee")) {
			return false;
		}
		break;
	case 2:
		v_1 = (($this.limit - $this.cursor) | 0);
	golab0:
		while (true) {
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, PorterStemmer.g_v, 97, 121)) {
					break lab1;
				}
				break golab0;
			}
			if ($this.cursor <= $this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
		}
		$this.cursor = (($this.limit - v_1) | 0);
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		v_3 = (($this.limit - $this.cursor) | 0);
		among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_1, 13);
		if (among_var === 0) {
			return false;
		}
		$this.cursor = (($this.limit - v_3) | 0);
		switch (among_var) {
		case 0:
			return false;
		case 1:
			c = cursor$0 = $this.cursor;
			c_bra$0 = cursor$0;
			adjustment$0 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$0, cursor$0, "e");
			if (cursor$0 <= $this.bra) {
				$this.bra = ($this.bra + adjustment$0) | 0;
			}
			if (c_bra$0 <= $this.ket) {
				$this.ket = ($this.ket + adjustment$0) | 0;
			}
			$this.cursor = c;
			break;
		case 2:
			$this.ket = cursor$1 = $this.cursor;
			if (cursor$1 <= $this.limit_backward) {
				return false;
			}
			($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
			$this.bra = $this.cursor;
			if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
				return false;
			}
			break;
		case 3:
			if ($this.cursor !== $this.I_p1) {
				return false;
			}
			v_4 = (($this.limit - $this.cursor) | 0);
			if (! PorterStemmer$r_shortv$LPorterStemmer$($this)) {
				return false;
			}
			cursor$2 = $this.cursor = (($this.limit - v_4) | 0);
			c = cursor$2;
			c_bra$1 = cursor$2;
			adjustment$1 = BaseStemmer$replace_s$LBaseStemmer$IIS($this, cursor$2, cursor$2, "e");
			if (cursor$2 <= $this.bra) {
				$this.bra = ($this.bra + adjustment$1) | 0;
			}
			if (c_bra$1 <= $this.ket) {
				$this.ket = ($this.ket + adjustment$1) | 0;
			}
			$this.cursor = c;
			break;
		}
		break;
	}
	return true;
};

PorterStemmer.r_Step_1b$LPorterStemmer$ = PorterStemmer$r_Step_1b$LPorterStemmer$;

PorterStemmer.prototype.r_Step_1c$ = function () {
	var v_1;
	var lab0;
	var lab1;
	var lab3;
	var $__jsx_postinc_t;
	this.ket = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "y")) {
				break lab1;
			}
			break lab0;
		}
		this.cursor = ((this.limit - v_1) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "Y")) {
			return false;
		}
	}
	this.bra = this.cursor;
golab2:
	while (true) {
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
				break lab3;
			}
			break golab2;
		}
		if (this.cursor <= this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "i") ? false : true);
};

PorterStemmer.prototype.r_Step_1c = PorterStemmer.prototype.r_Step_1c$;

function PorterStemmer$r_Step_1c$LPorterStemmer$($this) {
	var v_1;
	var lab0;
	var lab1;
	var lab3;
	var $__jsx_postinc_t;
	$this.ket = $this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "y")) {
				break lab1;
			}
			break lab0;
		}
		$this.cursor = (($this.limit - v_1) | 0);
		if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "Y")) {
			return false;
		}
	}
	$this.bra = $this.cursor;
golab2:
	while (true) {
		lab3 = true;
	lab3:
		while (lab3 === true) {
			lab3 = false;
			if (! BaseStemmer$in_grouping_b$LBaseStemmer$AIII($this, PorterStemmer.g_v, 97, 121)) {
				break lab3;
			}
			break golab2;
		}
		if ($this.cursor <= $this.limit_backward) {
			return false;
		}
		($__jsx_postinc_t = $this.cursor, $this.cursor = ($__jsx_postinc_t - 1) | 0, $__jsx_postinc_t);
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "i") ? false : true);
};

PorterStemmer.r_Step_1c$LPorterStemmer$ = PorterStemmer$r_Step_1c$LPorterStemmer$;

PorterStemmer.prototype.r_Step_2$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_3, 20);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "tion")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ence")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ance")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "able")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ent")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "e")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ize")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ate")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "al")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "al")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ful")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ous")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ive")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ble")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.prototype.r_Step_2 = PorterStemmer.prototype.r_Step_2$;

function PorterStemmer$r_Step_2$LPorterStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_3, 20);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "tion")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ence")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ance")) {
			return false;
		}
		break;
	case 4:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "able")) {
			return false;
		}
		break;
	case 5:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ent")) {
			return false;
		}
		break;
	case 6:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "e")) {
			return false;
		}
		break;
	case 7:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ize")) {
			return false;
		}
		break;
	case 8:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ate")) {
			return false;
		}
		break;
	case 9:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "al")) {
			return false;
		}
		break;
	case 10:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "al")) {
			return false;
		}
		break;
	case 11:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ful")) {
			return false;
		}
		break;
	case 12:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ous")) {
			return false;
		}
		break;
	case 13:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ive")) {
			return false;
		}
		break;
	case 14:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ble")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.r_Step_2$LPorterStemmer$ = PorterStemmer$r_Step_2$LPorterStemmer$;

PorterStemmer.prototype.r_Step_3$ = function () {
	var among_var;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_4, 7);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "al")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "ic")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.prototype.r_Step_3 = PorterStemmer.prototype.r_Step_3$;

function PorterStemmer$r_Step_3$LPorterStemmer$($this) {
	var among_var;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_4, 7);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "al")) {
			return false;
		}
		break;
	case 2:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "ic")) {
			return false;
		}
		break;
	case 3:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.r_Step_3$LPorterStemmer$ = PorterStemmer$r_Step_3$LPorterStemmer$;

PorterStemmer.prototype.r_Step_4$ = function () {
	var among_var;
	var v_1;
	var lab0;
	var lab1;
	var cursor$0;
	this.ket = this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I(this, PorterStemmer.a_5, 19);
	if (among_var === 0) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	if (! (! (this.I_p2 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	case 2:
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_1 = ((this.limit - this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "s")) {
					break lab1;
				}
				break lab0;
			}
			this.cursor = ((this.limit - v_1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "t")) {
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.prototype.r_Step_4 = PorterStemmer.prototype.r_Step_4$;

function PorterStemmer$r_Step_4$LPorterStemmer$($this) {
	var among_var;
	var v_1;
	var lab0;
	var lab1;
	var cursor$0;
	$this.ket = $this.cursor;
	among_var = BaseStemmer$find_among_b$LBaseStemmer$ALAmong$I($this, PorterStemmer.a_5, 19);
	if (among_var === 0) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	if (! (! ($this.I_p2 <= cursor$0) ? false : true)) {
		return false;
	}
	switch (among_var) {
	case 0:
		return false;
	case 1:
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	case 2:
		lab0 = true;
	lab0:
		while (lab0 === true) {
			lab0 = false;
			v_1 = (($this.limit - $this.cursor) | 0);
			lab1 = true;
		lab1:
			while (lab1 === true) {
				lab1 = false;
				if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "s")) {
					break lab1;
				}
				break lab0;
			}
			$this.cursor = (($this.limit - v_1) | 0);
			if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "t")) {
				return false;
			}
		}
		if (! BaseStemmer$slice_from$LBaseStemmer$S($this, "")) {
			return false;
		}
		break;
	}
	return true;
};

PorterStemmer.r_Step_4$LPorterStemmer$ = PorterStemmer$r_Step_4$LPorterStemmer$;

PorterStemmer.prototype.r_Step_5a$ = function () {
	var v_1;
	var v_2;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	this.ket = this.cursor;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "e")) {
		return false;
	}
	this.bra = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = ((this.limit - this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! (! (this.I_p2 <= this.cursor) ? false : true)) {
				break lab1;
			}
			break lab0;
		}
		cursor$0 = this.cursor = ((this.limit - v_1) | 0);
		if (! (! (this.I_p1 <= cursor$0) ? false : true)) {
			return false;
		}
		v_2 = ((this.limit - this.cursor) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			if (! PorterStemmer$r_shortv$LPorterStemmer$(this)) {
				break lab2;
			}
			return false;
		}
		this.cursor = ((this.limit - v_2) | 0);
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

PorterStemmer.prototype.r_Step_5a = PorterStemmer.prototype.r_Step_5a$;

function PorterStemmer$r_Step_5a$LPorterStemmer$($this) {
	var v_1;
	var v_2;
	var lab0;
	var lab1;
	var lab2;
	var cursor$0;
	$this.ket = $this.cursor;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "e")) {
		return false;
	}
	$this.bra = $this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		v_1 = (($this.limit - $this.cursor) | 0);
		lab1 = true;
	lab1:
		while (lab1 === true) {
			lab1 = false;
			if (! (! ($this.I_p2 <= $this.cursor) ? false : true)) {
				break lab1;
			}
			break lab0;
		}
		cursor$0 = $this.cursor = (($this.limit - v_1) | 0);
		if (! (! ($this.I_p1 <= cursor$0) ? false : true)) {
			return false;
		}
		v_2 = (($this.limit - $this.cursor) | 0);
		lab2 = true;
	lab2:
		while (lab2 === true) {
			lab2 = false;
			if (! PorterStemmer$r_shortv$LPorterStemmer$($this)) {
				break lab2;
			}
			return false;
		}
		$this.cursor = (($this.limit - v_2) | 0);
	}
	return (! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

PorterStemmer.r_Step_5a$LPorterStemmer$ = PorterStemmer$r_Step_5a$LPorterStemmer$;

PorterStemmer.prototype.r_Step_5b$ = function () {
	var cursor$0;
	this.ket = this.cursor;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "l")) {
		return false;
	}
	this.bra = cursor$0 = this.cursor;
	return (! (! (this.I_p2 <= cursor$0) ? false : true) ? false : ! BaseStemmer$eq_s_b$LBaseStemmer$IS(this, 1, "l") ? false : ! BaseStemmer$slice_from$LBaseStemmer$S(this, "") ? false : true);
};

PorterStemmer.prototype.r_Step_5b = PorterStemmer.prototype.r_Step_5b$;

function PorterStemmer$r_Step_5b$LPorterStemmer$($this) {
	var cursor$0;
	$this.ket = $this.cursor;
	if (! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "l")) {
		return false;
	}
	$this.bra = cursor$0 = $this.cursor;
	return (! (! ($this.I_p2 <= cursor$0) ? false : true) ? false : ! BaseStemmer$eq_s_b$LBaseStemmer$IS($this, 1, "l") ? false : ! BaseStemmer$slice_from$LBaseStemmer$S($this, "") ? false : true);
};

PorterStemmer.r_Step_5b$LPorterStemmer$ = PorterStemmer$r_Step_5b$LPorterStemmer$;

PorterStemmer.prototype.stem$ = function () {
	var v_1;
	var v_2;
	var v_3;
	var v_4;
	var v_5;
	var v_10;
	var v_11;
	var v_12;
	var v_13;
	var v_14;
	var v_15;
	var v_16;
	var v_18;
	var v_19;
	var v_20;
	var lab0;
	var lab1;
	var lab3;
	var lab5;
	var lab6;
	var lab8;
	var lab10;
	var lab12;
	var lab14;
	var lab15;
	var lab16;
	var lab17;
	var lab18;
	var lab19;
	var lab20;
	var lab21;
	var lab22;
	var lab23;
	var lab25;
	var lab27;
	var cursor$0;
	var cursor$1;
	var limit$0;
	var cursor$2;
	var cursor$3;
	var limit$1;
	var cursor$4;
	var limit$2;
	var cursor$5;
	var limit$3;
	var cursor$6;
	var limit$4;
	var cursor$7;
	var limit$5;
	var cursor$8;
	var limit$6;
	var cursor$9;
	var limit$7;
	var cursor$10;
	var cursor$11;
	var cursor$12;
	var $__jsx_postinc_t;
	this.B_Y_found = false;
	v_1 = this.cursor;
	lab0 = true;
lab0:
	while (lab0 === true) {
		lab0 = false;
		this.bra = this.cursor;
		if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "y")) {
			break lab0;
		}
		this.ket = this.cursor;
		if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "Y")) {
			return false;
		}
		this.B_Y_found = true;
	}
	cursor$1 = this.cursor = v_1;
	v_2 = cursor$1;
	lab1 = true;
lab1:
	while (lab1 === true) {
		lab1 = false;
	replab2:
		while (true) {
			v_3 = this.cursor;
			lab3 = true;
		lab3:
			while (lab3 === true) {
				lab3 = false;
			golab4:
				while (true) {
					v_4 = this.cursor;
					lab5 = true;
				lab5:
					while (lab5 === true) {
						lab5 = false;
						if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
							break lab5;
						}
						this.bra = this.cursor;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "y")) {
							break lab5;
						}
						this.ket = this.cursor;
						this.cursor = v_4;
						break golab4;
					}
					cursor$0 = this.cursor = v_4;
					if (cursor$0 >= this.limit) {
						break lab3;
					}
					($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "Y")) {
					return false;
				}
				this.B_Y_found = true;
				continue replab2;
			}
			this.cursor = v_3;
			break replab2;
		}
	}
	cursor$2 = this.cursor = v_2;
	this.I_p1 = limit$0 = this.limit;
	this.I_p2 = limit$0;
	v_5 = cursor$2;
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
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
				if (! BaseStemmer$in_grouping$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
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
				if (! BaseStemmer$out_grouping$LBaseStemmer$AIII(this, PorterStemmer.g_v, 97, 121)) {
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
	cursor$3 = this.cursor = v_5;
	this.limit_backward = cursor$3;
	cursor$4 = this.cursor = limit$1 = this.limit;
	v_10 = ((limit$1 - cursor$4) | 0);
	lab15 = true;
lab15:
	while (lab15 === true) {
		lab15 = false;
		if (! PorterStemmer$r_Step_1a$LPorterStemmer$(this)) {
			break lab15;
		}
	}
	cursor$5 = this.cursor = (((limit$2 = this.limit) - v_10) | 0);
	v_11 = ((limit$2 - cursor$5) | 0);
	lab16 = true;
lab16:
	while (lab16 === true) {
		lab16 = false;
		if (! PorterStemmer$r_Step_1b$LPorterStemmer$(this)) {
			break lab16;
		}
	}
	cursor$6 = this.cursor = (((limit$3 = this.limit) - v_11) | 0);
	v_12 = ((limit$3 - cursor$6) | 0);
	lab17 = true;
lab17:
	while (lab17 === true) {
		lab17 = false;
		if (! PorterStemmer$r_Step_1c$LPorterStemmer$(this)) {
			break lab17;
		}
	}
	cursor$7 = this.cursor = (((limit$4 = this.limit) - v_12) | 0);
	v_13 = ((limit$4 - cursor$7) | 0);
	lab18 = true;
lab18:
	while (lab18 === true) {
		lab18 = false;
		if (! PorterStemmer$r_Step_2$LPorterStemmer$(this)) {
			break lab18;
		}
	}
	cursor$8 = this.cursor = (((limit$5 = this.limit) - v_13) | 0);
	v_14 = ((limit$5 - cursor$8) | 0);
	lab19 = true;
lab19:
	while (lab19 === true) {
		lab19 = false;
		if (! PorterStemmer$r_Step_3$LPorterStemmer$(this)) {
			break lab19;
		}
	}
	cursor$9 = this.cursor = (((limit$6 = this.limit) - v_14) | 0);
	v_15 = ((limit$6 - cursor$9) | 0);
	lab20 = true;
lab20:
	while (lab20 === true) {
		lab20 = false;
		if (! PorterStemmer$r_Step_4$LPorterStemmer$(this)) {
			break lab20;
		}
	}
	cursor$10 = this.cursor = (((limit$7 = this.limit) - v_15) | 0);
	v_16 = ((limit$7 - cursor$10) | 0);
	lab21 = true;
lab21:
	while (lab21 === true) {
		lab21 = false;
		if (! PorterStemmer$r_Step_5a$LPorterStemmer$(this)) {
			break lab21;
		}
	}
	this.cursor = ((this.limit - v_16) | 0);
	lab22 = true;
lab22:
	while (lab22 === true) {
		lab22 = false;
		if (! PorterStemmer$r_Step_5b$LPorterStemmer$(this)) {
			break lab22;
		}
	}
	cursor$12 = this.cursor = this.limit_backward;
	v_18 = cursor$12;
	lab23 = true;
lab23:
	while (lab23 === true) {
		lab23 = false;
		if (! this.B_Y_found) {
			break lab23;
		}
	replab24:
		while (true) {
			v_19 = this.cursor;
			lab25 = true;
		lab25:
			while (lab25 === true) {
				lab25 = false;
			golab26:
				while (true) {
					v_20 = this.cursor;
					lab27 = true;
				lab27:
					while (lab27 === true) {
						lab27 = false;
						this.bra = this.cursor;
						if (! BaseStemmer$eq_s$LBaseStemmer$IS(this, 1, "Y")) {
							break lab27;
						}
						this.ket = this.cursor;
						this.cursor = v_20;
						break golab26;
					}
					cursor$11 = this.cursor = v_20;
					if (cursor$11 >= this.limit) {
						break lab25;
					}
					($__jsx_postinc_t = this.cursor, this.cursor = ($__jsx_postinc_t + 1) | 0, $__jsx_postinc_t);
				}
				if (! BaseStemmer$slice_from$LBaseStemmer$S(this, "y")) {
					return false;
				}
				continue replab24;
			}
			this.cursor = v_19;
			break replab24;
		}
	}
	this.cursor = v_18;
	return true;
};

PorterStemmer.prototype.stem = PorterStemmer.prototype.stem$;

PorterStemmer.prototype.equals$X = function (o) {
	return o instanceof PorterStemmer;
};

PorterStemmer.prototype.equals = PorterStemmer.prototype.equals$X;

function PorterStemmer$equals$LPorterStemmer$X($this, o) {
	return o instanceof PorterStemmer;
};

PorterStemmer.equals$LPorterStemmer$X = PorterStemmer$equals$LPorterStemmer$X;

PorterStemmer.prototype.hashCode$ = function () {
	var classname;
	var hash;
	var i;
	var char;
	classname = "PorterStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

PorterStemmer.prototype.hashCode = PorterStemmer.prototype.hashCode$;

function PorterStemmer$hashCode$LPorterStemmer$($this) {
	var classname;
	var hash;
	var i;
	var char;
	classname = "PorterStemmer";
	hash = 0;
	for (i = 0; i < classname.length; i++) {
		char = classname.charCodeAt(i);
		hash = (hash << 5) - hash + char;
		hash = hash & hash;
	}
	return (hash | 0);
};

PorterStemmer.hashCode$LPorterStemmer$ = PorterStemmer$hashCode$LPorterStemmer$;

PorterStemmer.serialVersionUID = 1;
$__jsx_lazy_init(PorterStemmer, "methodObject", function () {
	return new PorterStemmer();
});
$__jsx_lazy_init(PorterStemmer, "a_0", function () {
	return [ new Among("s", -1, 3), new Among("ies", 0, 2), new Among("sses", 0, 1), new Among("ss", 0, -1) ];
});
$__jsx_lazy_init(PorterStemmer, "a_1", function () {
	return [ new Among("", -1, 3), new Among("bb", 0, 2), new Among("dd", 0, 2), new Among("ff", 0, 2), new Among("gg", 0, 2), new Among("bl", 0, 1), new Among("mm", 0, 2), new Among("nn", 0, 2), new Among("pp", 0, 2), new Among("rr", 0, 2), new Among("at", 0, 1), new Among("tt", 0, 2), new Among("iz", 0, 1) ];
});
$__jsx_lazy_init(PorterStemmer, "a_2", function () {
	return [ new Among("ed", -1, 2), new Among("eed", 0, 1), new Among("ing", -1, 2) ];
});
$__jsx_lazy_init(PorterStemmer, "a_3", function () {
	return [ new Among("anci", -1, 3), new Among("enci", -1, 2), new Among("abli", -1, 4), new Among("eli", -1, 6), new Among("alli", -1, 9), new Among("ousli", -1, 12), new Among("entli", -1, 5), new Among("aliti", -1, 10), new Among("biliti", -1, 14), new Among("iviti", -1, 13), new Among("tional", -1, 1), new Among("ational", 10, 8), new Among("alism", -1, 10), new Among("ation", -1, 8), new Among("ization", 13, 7), new Among("izer", -1, 7), new Among("ator", -1, 8), new Among("iveness", -1, 13), new Among("fulness", -1, 11), new Among("ousness", -1, 12) ];
});
$__jsx_lazy_init(PorterStemmer, "a_4", function () {
	return [ new Among("icate", -1, 2), new Among("ative", -1, 3), new Among("alize", -1, 1), new Among("iciti", -1, 2), new Among("ical", -1, 2), new Among("ful", -1, 3), new Among("ness", -1, 3) ];
});
$__jsx_lazy_init(PorterStemmer, "a_5", function () {
	return [ new Among("ic", -1, 1), new Among("ance", -1, 1), new Among("ence", -1, 1), new Among("able", -1, 1), new Among("ible", -1, 1), new Among("ate", -1, 1), new Among("ive", -1, 1), new Among("ize", -1, 1), new Among("iti", -1, 1), new Among("al", -1, 1), new Among("ism", -1, 1), new Among("ion", -1, 2), new Among("er", -1, 1), new Among("ous", -1, 1), new Among("ant", -1, 1), new Among("ent", -1, 1), new Among("ment", 15, 1), new Among("ement", 16, 1), new Among("ou", -1, 1) ];
});
PorterStemmer.g_v = [ 17, 65, 16, 1 ];
PorterStemmer.g_v_WXY = [ 1, 17, 65, 208, 1 ];

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
	"src/porter-stemmer.jsx": {
		PorterStemmer: PorterStemmer,
		PorterStemmer$: PorterStemmer
	}
};


})(JSX);

var Among = JSX.require("src/among.jsx").Among;
var Among$SII = JSX.require("src/among.jsx").Among$SII;
var Stemmer = JSX.require("src/stemmer.jsx").Stemmer;
var BaseStemmer = JSX.require("src/base-stemmer.jsx").BaseStemmer;
var PorterStemmer = JSX.require("src/porter-stemmer.jsx").PorterStemmer;
