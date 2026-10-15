// method_tracer.js - 追踪 Activity.onCreate 调用
send({ type: "status", payload: { message: "开始注入 Hook" } });

if (Java.available) {
    Java.perform(function () {
        var Activity = Java.use("android.app.Activity");

        Activity.onCreate.overload("android.os.Bundle").implementation = function (bundle) {
            send({
                type: "method_call",
                payload: {
                    class: "android.app.Activity",
                    method: "onCreate",
                    timestamp: Date.now(),
                    thread_id: Process.getCurrentThreadId(),
                    has_bundle: bundle !== null
                }
            });
            return this.onCreate(bundle);
        };

        send({ type: "status", payload: { message: "Hook 已安装: Activity.onCreate" } });
    });
} else {
    send({ type: "error", payload: { message: "Java runtime 不可用" } });
}
