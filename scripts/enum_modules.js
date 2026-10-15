// enum_modules.js - 枚举已加载的原生模块
send({ type: "status", payload: { message: "开始枚举原生模块" } });

var modules = Process.enumerateModules();

modules.forEach(function (m) {
    send({
        type: "module",
        payload: {
            name: m.name,
            base: m.base.toString(),
            size: m.size,
            path: m.path
        }
    });
});

send({ type: "status", payload: { message: "枚举完成", count: modules.length } });
