// Static imports.
import rootConst from "/static/absolute_root.js";
import secondRootConst from "/absolute_root.js";
import testConst from "./module_test.js";
import * as NewModule from "./module_test.js";
import { testConst as alias } from "./module_test.js";
import { firstConst, secondConst } from "./module_test.js";
import {
    firstVar1 as firstVarAlias,
    $second_var_2 as secondVarAlias,
} from "./module_test.js";
import relativeModule from "../nested/js/nested.js";

// Dynamic imports.
const dynamicModule = import("./module_test.js");

// Modules exports to aggregate modules.
export * from "./module_test.js";
export { testConst } from "./module_test.js";
export {
    firstVar as firstVarAlias,
    secondVar as secondVarAlias,
} from "./module_test.js";
