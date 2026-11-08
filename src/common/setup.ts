// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

import * as fs from 'fs-extra';
import { SERVER_CONFIG_PATH } from './constants';

export interface IServerInfo {
    name: string;
    module: string;
}

export interface IServerConfig {
    mode: 'python' | 'command';
    serverInfo: IServerInfo;
    languageIds: string[];
    command?: string;
    commandArgs?: string[];
    pythonCommand?: string;
}

export function loadServerDefaults(): IServerConfig {
    return fs.readJsonSync(SERVER_CONFIG_PATH) as IServerConfig;
}
