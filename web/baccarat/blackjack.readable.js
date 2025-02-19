// Blackjack Game Module
"use strict";

// Initialize webpack chunk
(self.webpackChunk_frontend_evo_r2_ = self.webpackChunk_frontend_evo_r2_ || []).push([
    [46350], 
    {
        // CSS Styles Module
        677457: (file, exports, require) => {
            require.d(exports, {
                Animations: () => cssClasses
            });
            
            const cssClasses = {
                arrowLeft: "arrowLeft--2cd1a",
                arrowRight: "arrowRight--de11b",
                playAnimation: "playAnimation--32b90",
                arrowLeftMoveKeyframes: "arrowLeftMoveKeyframes--9e70a",
                arrowRightMoveKeyframes: "arrowRightMoveKeyframes--12042"
            };
        },

        // Layout Module
        940851: (file, exports, require) => {
            require.d(exports, {
                Layout: () => layoutClasses
            });
            
            const layoutClasses = {
                wrapper: "wrapper--ea24d",
                lg: "lg--422c8",
                md: "md--15b20",
                sm: "sm--e226f",
                xs: "xs--00b48",
                coreContainer: "coreContainer--26c7d",
                headerOffset: "headerOffset--19d82",
                contentContainer: "contentContainer--d1e6f",
                topGradientLine: "topGradientLine--cb313",
                appearing: "appearing--a7aa6",
                scaleXAnimationKeyframes: "scaleXAnimationKeyframes--fe6c0",
                shortenAnimation: "shortenAnimation--9b2b6",
                disappearing: "disappearing--235ce",
                radialGradientBackground: "radialGradientBackground--34177",
                withAmbientGradient: "withAmbientGradient--29e03",
                opacityAnimationKeyframes: "opacityAnimationKeyframes--ced30",
                textContainer: "textContainer--ed652",
                withAmountLabel: "withAmountLabel--35449",
                label: "label--ce5af",
                amountTextContainer: "amountTextContainer--ffd5e",
                amount: "amount--adfea",
                winAmountAppearingKeyframes: "winAmountAppearingKeyframes--10d71",
                scaleAnimationKeyframes: "scaleAnimationKeyframes--e0414",
                winAmountDisappearingKeyframes: "winAmountDisappearingKeyframes--f81cc"
            };
        },

        // State Management Module (using MobX)
        56761: (file, exports, require) => {
            require.d(exports, {
                fromPromise: () => fromPromise,
                subscribingObservable: () => subscribingObservable,
                EMPTY_FUNC: () => EMPTY_FUNC
            });

            const mobx = require(697971);
            const EMPTY_FUNC = function() {};

            // Utility function to check state
            function assertState(condition, message = "Illegal state") {
                if (!condition) {
                    throw new Error("[mobx-utils] " + message);
                }
            }

            // Get all property names including prototype chain
            function getAllPropertyNames(obj) {
                if (!obj || obj === Object.prototype) return [];
                return Object.getOwnPropertyNames(obj)
                    .concat(getAllPropertyNames(Object.getPrototypeOf(obj)) || []);
            }

            // Get unique property names excluding constructor and private props
            function getUniquePropertyNames(obj) {
                return getAllPropertyNames(obj)
                    .filter((name, index, array) => array.indexOf(name) === index)
                    .filter(name => name !== "constructor" && !name.includes("__"));
            }

            // Promise state handler
            function handlePromiseState(handlers) {
                switch (this.state) {
                    case "pending":
                        return handlers.pending && handlers.pending(this.value);
                    case "rejected":
                        return handlers.rejected && handlers.rejected(this.value);
                    case "fulfilled":
                        return handlers.fulfilled ? handlers.fulfilled(this.value) : this.value;
                }
            }

            // Create observable from promise
            function fromPromise(promise, oldPromise) {
                assertState(arguments.length <= 2, "fromPromise expects up to two arguments");
                assertState(
                    typeof promise === "function" || 
                    (typeof promise === "object" && promise && typeof promise.then === "function"),
                    "Please pass a promise or function to fromPromise"
                );

                if (promise.isPromiseBasedObservable === true) {
                    return promise;
                }

                if (typeof promise === "function") {
                    promise = new Promise(promise);
                }

                const observable = promise;

                promise.then(
                    mobx.action("observableFromPromise-resolve", value => {
                        observable.value = value;
                        observable.state = "fulfilled";
                    }),
                    mobx.action("observableFromPromise-reject", error => {
                        observable.value = error;
                        observable.state = "rejected";
                    })
                );

                observable.isPromiseBasedObservable = true;
                observable.case = handlePromiseState;

                const initialValue = oldPromise && oldPromise.state === "fulfilled" 
                    ? oldPromise.value 
                    : undefined;

                mobx.extendObservable(
                    observable,
                    {
                        value: initialValue,
                        state: "pending"
                    },
                    {},
                    { deep: false }
                );

                return observable;
            }

            // Add static methods to fromPromise
            fromPromise.reject = mobx.action("fromPromise.reject", error => {
                const observable = fromPromise(Promise.reject(error));
                observable.state = "rejected";
                observable.value = error;
                return observable;
            });

            fromPromise.resolve = mobx.action("fromPromise.resolve", value => {
                const observable = fromPromise(Promise.resolve(value));
                observable.state = "fulfilled";
                observable.value = value;
                return observable;
            });

            // Create subscribing observable
            function subscribingObservable(subscriber, onDispose = EMPTY_FUNC, initialValue = undefined) {
                let subscribed = false;
                let disposed = false;
                let currentValue = initialValue;

                const cleanup = () => {
                    if (subscribed) {
                        subscribed = false;
                        onDispose();
                    }
                };

                const observable = mobx.createAtom(
                    "ResourceBasedObservable",
                    () => {
                        assertState(!subscribed && !disposed);
                        subscribed = true;
                        subscriber(value => {
                            mobx.runInAction(() => {
                                currentValue = value;
                                observable.reportChanged();
                            });
                        });
                    },
                    cleanup
                );

                return {
                    current: () => {
                        assertState(!disposed, "subscribingObservable has already been disposed");
                        if (!observable.reportObserved() && !subscribed) {
                            console.warn(
                                "Called `get` of a subscribingObservable outside a reaction. " +
                                "Current value will be returned but no new subscription has started"
                            );
                        }
                        return currentValue;
                    },
                    dispose: () => {
                        disposed = true;
                        cleanup();
                    },
                    isAlive: () => subscribed
                };
            }
        }
    }
]); 