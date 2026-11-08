// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as fsapi from 'fs-extra';
import { Disposable, env, extensions, LogOutputChannel } from 'vscode';
import { State } from 'vscode-languageclient';
import {
    LanguageClient,
    LanguageClientOptions,
    RevealOutputChannelOn,
    ServerOptions,
} from 'vscode-languageclient/node';
import { DEBUG_SERVER_SCRIPT_PATH, SERVER_SCRIPT_PATH } from './constants';
import { traceError, traceInfo, traceVerbose } from './log/logging';
import { getDebuggerPath } from './python';
import { getExtensionSettings, getGlobalSettings, getWorkspaceSettings, ISettings } from './settings';
import { getLSClientTraceLevel, getProjectRoot } from './utilities';
import { isVirtualWorkspace } from './vscodeapi';
import { loadServerDefaults } from './setup';

export type IInitOptions = { settings: ISettings[]; globalSettings: ISettings };

async function createServer(
    settings: ISettings,
    serverId: string,
    serverName: string,
    outputChannel: LogOutputChannel,
    initializationOptions: IInitOptions,
): Promise<LanguageClient> {
    const cwd = settings.cwd;
    const serverConfig = loadServerDefaults();
    const documentSelector: LanguageClientOptions['documentSelector'] = isVirtualWorkspace()
        ? serverConfig.languageIds.map((language) => ({ language }))
        : serverConfig.languageIds.flatMap((language) => [
              { scheme: 'file' as const, language },
              { scheme: 'untitled' as const, language },
              { scheme: 'vscode-notebook' as const, language },
              { scheme: 'vscode-notebook-cell' as const, language },
          ]);

    if (serverConfig.mode === 'command') {
        const configuredPath = settings.path;
        const command = configuredPath[0] || serverConfig.command;
        if (!command) {
            throw new Error('LSP_COMMAND must be configured for command launch mode.');
        }
        const args = [
            ...(configuredPath.length > 0
                ? configuredPath.slice(1)
                : serverConfig.commandArgs ?? []),
            ...settings.args,
        ];
        traceInfo(`Server run command: ${[command, ...args].join(' ')}`);
        const serverOptions: ServerOptions = {
            command,
            args,
            options: {
                cwd,
                env: {
                    ...process.env,
                    LS_SHOW_NOTIFICATION: settings.showNotifications,
                },
            },
        };
        const clientOptions: LanguageClientOptions = {
            documentSelector,
            outputChannel,
            traceOutputChannel: outputChannel,
            revealOutputChannelOn: RevealOutputChannelOn.Never,
            initializationOptions,
        };
        return new LanguageClient(serverId, serverName, serverOptions, clientOptions);
    }

    const command = settings.interpreter[0] || serverConfig.pythonCommand || 'python3';

    // Set debugger path needed for debugging python code.
    const newEnv = { ...process.env };
    const debuggerPath = await getDebuggerPath();
    const isDebugScript = await fsapi.pathExists(DEBUG_SERVER_SCRIPT_PATH);
    if (newEnv.USE_DEBUGPY && debuggerPath) {
        newEnv.DEBUGPY_PATH = debuggerPath;
    } else {
        newEnv.USE_DEBUGPY = 'False';
    }

    // Set import strategy
    newEnv.LS_IMPORT_STRATEGY = settings.importStrategy;

    // Set notification type
    newEnv.LS_SHOW_NOTIFICATION = settings.showNotifications;

    const args =
        newEnv.USE_DEBUGPY === 'False' || !isDebugScript
            ? settings.interpreter.slice(1).concat([SERVER_SCRIPT_PATH])
            : settings.interpreter.slice(1).concat([DEBUG_SERVER_SCRIPT_PATH]);
    traceInfo(`Server run command: ${[command, ...args].join(' ')}`);

    const serverOptions: ServerOptions = {
        command,
        args,
        options: { cwd, env: newEnv },
    };

    // Options to control the language client
    const clientOptions: LanguageClientOptions = {
        documentSelector,
        outputChannel: outputChannel,
        traceOutputChannel: outputChannel,
        revealOutputChannelOn: RevealOutputChannelOn.Never,
        initializationOptions,
    };

    return new LanguageClient(serverId, serverName, serverOptions, clientOptions);
}

let _disposables: Disposable[] = [];
export async function restartServer(
    serverId: string,
    serverName: string,
    outputChannel: LogOutputChannel,
    lsClient?: LanguageClient,
): Promise<LanguageClient | undefined> {
    if (lsClient) {
        traceInfo(`Server: Stop requested`);
        try {
            await lsClient.stop();
        } catch (ex) {
            traceError(`Server: Stop failed: ${ex}`);
        }
    }
    _disposables.forEach((d) => d.dispose());
    _disposables = [];
    const serverConfig = loadServerDefaults();
    const usePythonExtension =
        serverConfig.mode === 'python' && Boolean(extensions.getExtension('ms-python.python'));
    const projectRoot = await getProjectRoot();
    const workspaceSetting = await getWorkspaceSettings(
        serverId,
        projectRoot,
        usePythonExtension,
    );

    const newLSClient = await createServer(workspaceSetting, serverId, serverName, outputChannel, {
        settings: await getExtensionSettings(serverId, usePythonExtension),
        globalSettings: await getGlobalSettings(serverId, false),
    });
    traceInfo(`Server: Start requested.`);
    _disposables.push(
        newLSClient.onDidChangeState((e) => {
            switch (e.newState) {
                case State.Stopped:
                    traceVerbose(`Server State: Stopped`);
                    break;
                case State.Starting:
                    traceVerbose(`Server State: Starting`);
                    break;
                case State.Running:
                    traceVerbose(`Server State: Running`);
                    break;
            }
        }),
    );
    try {
        await newLSClient.start();
    } catch (ex) {
        traceError(`Server: Start failed: ${ex}`);
        return undefined;
    }

    const level = getLSClientTraceLevel(outputChannel.logLevel, env.logLevel);
    await newLSClient.setTrace(level);
    return newLSClient;
}
