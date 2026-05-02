// Static imports.
import rootConst from "/static/absolute_root.js";
import testConst from "./module_test.js";
import * as NewModule from "./module_test.js";
import*as m from "./module_test.js";
import *as m from "./module_test.js";
import* as m from "./module_test.js";
import*  as  m from "./module_test.js";
import { testConst as alias } from "./module_test.js";
import { firstConst, secondConst } from "./module_test.js";
import {
    firstVar1 as firstVarAlias,
    $second_var_2 as secondVarAlias
} from "./module_test.js";
import relativeModule from "../nested/js/nested.js";

// Dynamic imports.
const dynamicModule = import("./module_test.js");

// Modules exports to aggregate modules.
export * from "./module_test.js";
export { testConst } from "./module_test.js";
export {
    firstVar as firstVarAlias,
    secondVar as secondVarAlias
} from "./module_test.js";

// ignore block comments
/* export * from "./module_test_missing.js"; */
/*
import rootConst from "/static/absolute_root_missing.js";
const dynamicModule = import("./module_test_missing.js");
*/

// ignore line comments
// import testConst from "./module_test_missing.js";
// const dynamicModule = import("./module_test_missing.js");

// imports inside string literals should be ignored
const msg = 'import { foo } from "./module_test_missing.js";';
const help = "import { bar } from './module_test_missing.js';";
const tmpl = `import { baz } from "./module_test_missing.js";`;
const dyn = 'const x = import("./module_test_missing.js");';

// an export without a from clause must not consume a subsequent import's from
export { testConst };
import { firstConst } from "./module_test.js";
// imports inside JSDoc block comments should be ignored even when a
// real import precedes them (guarding against (?s:.*?) cross-boundary matches)
import '../nested/js/nested.js';
/**
 * @example
 * import { something } from "./module_test_missing.js";
 */
function jsdocExample() {}
