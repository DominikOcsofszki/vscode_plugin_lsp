// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as vscode from 'vscode';
import { LanguageClient } from 'vscode-languageclient/node';
import { registerLogger, traceError, traceLog, traceVerbose } from './common/log/logging';
import {
    checkVersion,
    getInterpreterDetails,
    initializePython,
    onDidChangePythonInterpreter,
    resolveInterpreter,
} from './common/python';
import { restartServer } from './common/server';
import { checkIfConfigurationChanged, getInterpreterFromSetting } from './common/settings';
import { loadServerDefaults } from './common/setup';
import { LS_SERVER_RESTART_DELAY } from './common/constants';
import { getLSClientTraceLevel } from './common/utilities';
import { createOutputChannel, onDidChangeConfiguration, registerCommand } from './common/vscodeapi';

let lsClient: LanguageClient | undefined;
let isRestarting = false;
let restartTimer: NodeJS.Timeout | undefined;
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    // This is required to get server name and module. This should be
    // the first thing that we do in this extension.
    const serverInfo = loadServerDefaults();
    const serverName = serverInfo.serverInfo.name;
    const serverId = serverInfo.serverInfo.module;
    const pythonExtensionAvailable = Boolean(vscode.extensions.getExtension('ms-python.python'));

    // Setup logging
    const outputChannel = createOutputChannel(serverName);
    context.subscriptions.push(outputChannel, registerLogger(outputChannel));

    const changeLogLevel = async (c: vscode.LogLevel, g: vscode.LogLevel) => {
        const level = getLSClientTraceLevel(c, g);
        await lsClient?.setTrace(level);
    };

    context.subscriptions.push(
        outputChannel.onDidChangeLogLevel(async (e) => {
            await changeLogLevel(e, vscode.env.logLevel);
        }),
        vscode.env.onDidChangeLogLevel(async (e) => {
            await changeLogLevel(outputChannel.logLevel, e);
        }),
    );

    // Log Server information
    traceLog(`Name: ${serverInfo.serverInfo.name}`);
    traceLog(`Module: ${serverInfo.serverInfo.module}`);
    traceVerbose(`Full Server Info: ${JSON.stringify(serverInfo)}`);

    const runServer = async () => {
        if (isRestarting) {
            if (restartTimer) {
                clearTimeout(restartTimer);
            }
            restartTimer = setTimeout(runServer, LS_SERVER_RESTART_DELAY);
            return;
        }
        isRestarting = true;
        try {
            if (serverInfo.mode === 'command') {
                lsClient = await restartServer(serverId, serverName, outputChannel, lsClient);
                return;
            }

            if (!pythonExtensionAvailable) {
                const configuredInterpreter = getInterpreterFromSetting(serverId);
                traceVerbose(
                    `Using configured Python command: ${configuredInterpreter?.join(' ') || serverInfo.pythonCommand}`,
                );
                lsClient = await restartServer(serverId, serverName, outputChannel, lsClient);
                return;
            }

            const interpreter = getInterpreterFromSetting(serverId);
            if (interpreter && interpreter.length > 0) {
                const resolvedInterpreter = await resolveInterpreter(interpreter);
                if (
                    checkVersion(
                        resolvedInterpreter?.version,
                        resolvedInterpreter?.executable.uri?.fsPath,
                    )
                ) {
                    traceVerbose(
                        `Using interpreter from ${serverInfo.serverInfo.module}.interpreter: ${interpreter.join(' ')}`,
                    );
                    lsClient = await restartServer(serverId, serverName, outputChannel, lsClient);
                }
                return;
            }

            const interpreterDetails = await getInterpreterDetails();
            if (interpreterDetails.path) {
                traceVerbose(`Using interpreter from Python extension: ${interpreterDetails.path.join(' ')}`);
                lsClient = await restartServer(serverId, serverName, outputChannel, lsClient);
                return;
            }

            traceError(
                'Python interpreter missing:\r\n' +
                    '[Option 1] Select python interpreter using the ms-python.python.\r\n' +
                    `[Option 2] Set an interpreter using "${serverId}.interpreter" setting.\r\n` +
                    'Please use Python 3.12 or greater.',
            );
        } finally {
            isRestarting = false;
        }
    };

    if (serverInfo.mode === 'python' && pythonExtensionAvailable) {
        context.subscriptions.push(
            onDidChangePythonInterpreter(async () => {
                await runServer();
            }),
        );
    }

    context.subscriptions.push(
        onDidChangeConfiguration(async (e: vscode.ConfigurationChangeEvent) => {
            if (checkIfConfigurationChanged(e, serverId)) {
                await runServer();
            }
        }),
        registerCommand(`${serverId}.restart`, async () => {
            await runServer();
        }),
    );

    setImmediate(async () => {
        if (serverInfo.mode === 'command') {
            await runServer();
            return;
        }

        const interpreter = getInterpreterFromSetting(serverId);
        if (pythonExtensionAvailable && (interpreter === undefined || interpreter.length === 0)) {
            traceLog(`Python extension loading`);
            await initializePython(context.subscriptions);
            traceLog(`Python extension loaded`);
        } else {
            await runServer();
        }
    });
}

export async function deactivate(): Promise<void> {
    if (lsClient) {
        try {
            await lsClient.stop();
        } catch (ex) {
            traceError(`Server: Stop failed: ${ex}`);
        }
    }
}
