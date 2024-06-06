'use client'
import type { FC } from 'react'
import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useBoolean } from 'ahooks'
import cn from 'classnames'
import produce from 'immer'
import { useContext } from 'use-context-selector'
import ConfirmAddVar from './confirm-add-var'
import s from './style.module.css'
import PromptEditorHeightResizeWrap from './prompt-editor-height-resize-wrap'
import { type PromptVariable } from '@/models/debug'
import Tooltip from '@/app/components/base/tooltip'
import { AppType } from '@/types/app'
import { getNewVar, getVars } from '@/utils/var'
import { HelpCircle } from '@/app/components/base/icons/src/vender/line/general'
import AutomaticBtn from '@/app/components/app/configuration/config/automatic/automatic-btn'
import type { AutomaticRes } from '@/service/debug'
import GetAutomaticResModal from '@/app/components/app/configuration/config/automatic/get-automatic-res'
import PromptEditor from '@/app/components/base/prompt-editor'
import ConfigContext from '@/context/debug-configuration'
import { useModalContext } from '@/context/modal-context'
import type { ExternalDataTool } from '@/models/common'
import { useToastContext } from '@/app/components/base/toast'
import { useEventEmitterContextContext } from '@/context/event-emitter'
import { ADD_EXTERNAL_DATA_TOOL } from '@/app/components/app/configuration/config-var'
import { INSERT_VARIABLE_VALUE_BLOCK_COMMAND } from '@/app/components/base/prompt-editor/plugins/variable-block'
import { PROMPT_EDITOR_UPDATE_VALUE_BY_EVENT_EMITTER } from '@/app/components/base/prompt-editor/plugins/update-block'

export type ISimplePromptInput = {
  mode: AppType
  promptTemplate: string
  promptVariables: PromptVariable[]
  readonly?: boolean
  onChange?: (promp: string, promptVariables: PromptVariable[]) => void
}

const Prompt: FC<ISimplePromptInput> = ({
  mode,
  promptTemplate,
  promptVariables,
  readonly = false,
  onChange,
}) => {
  const { t } = useTranslation()
  const { eventEmitter } = useEventEmitterContextContext()
  const {
    modelConfig,
    dataSets,
    setModelConfig,
    setPrevPromptConfig,
    setIntroduction,
    hasSetBlockStatus,
    showSelectDataSet,
    externalDataToolsConfig,
    isAgent,
  } = useContext(ConfigContext)
  const { notify } = useToastContext()
  const { setShowExternalDataToolModal } = useModalContext()
  const handleOpenExternalDataToolModal = () => {
    setShowExternalDataToolModal({
      payload: {},
      onSaveCallback: (newExternalDataTool: ExternalDataTool) => {
        eventEmitter?.emit({
          type: ADD_EXTERNAL_DATA_TOOL,
          payload: newExternalDataTool,
        } as any)
        eventEmitter?.emit({
          type: INSERT_VARIABLE_VALUE_BLOCK_COMMAND,
          payload: newExternalDataTool.variable,
        } as any)
      },
      onValidateBeforeSaveCallback: (newExternalDataTool: ExternalDataTool) => {
        for (let i = 0; i < promptVariables.length; i++) {
          if (promptVariables[i].key === newExternalDataTool.variable) {
            notify({ type: 'error', message: t('appDebug.varKeyError.keyAlreadyExists', { key: promptVariables[i].key }) })
            return false
          }
        }

        return true
      },
    })
  }
  const promptVariablesObj = (() => {
    const obj: Record<string, boolean> = {}
    promptVariables.forEach((item) => {
      obj[item.key] = true
    })
    return obj
  })()

  const [newPromptVariables, setNewPromptVariables] = React.useState<PromptVariable[]>(promptVariables)
  const [newTemplates, setNewTemplates] = React.useState('')
  const [isShowConfirmAddVar, { setTrue: showConfirmAddVar, setFalse: hideConfirmAddVar }] = useBoolean(false)

  const handleChange = (newTemplates: string, keys: string[]) => {
    const newPromptVariables = keys.filter(key => !(key in promptVariablesObj) && !externalDataToolsConfig.find(item => item.variable === key)).map(key => getNewVar(key, ''))
    if (newPromptVariables.length > 0) {
      setNewPromptVariables(newPromptVariables)
      setNewTemplates(newTemplates)
      showConfirmAddVar()
      return
    }
    onChange?.(newTemplates, [])
  }

  const handleAutoAdd = (isAdd: boolean) => {
    return () => {
      onChange?.(newTemplates, isAdd ? newPromptVariables : [])
      hideConfirmAddVar()
    }
  }

  const [showAutomatic, { setTrue: showAutomaticTrue, setFalse: showAutomaticFalse }] = useBoolean(false)
  const handleAutomaticRes = (res: AutomaticRes) => {
    const newModelConfig = produce(modelConfig, (draft) => {
      draft.configs.prompt_template = res.prompt
      draft.configs.prompt_variables = res.variables.map(key => ({ key, name: key, type: 'string', required: true }))
    })
    setModelConfig(newModelConfig)
    setPrevPromptConfig(modelConfig.configs)
    if (mode !== AppType.completion)
      setIntroduction(res.opening_statement)
    showAutomaticFalse()
    eventEmitter?.emit({
      type: PROMPT_EDITOR_UPDATE_VALUE_BY_EVENT_EMITTER,
      payload: res.prompt,
    } as any)
  }
  const minHeight = 228
  const [editorHeight, setEditorHeight] = useState(minHeight)

  return (
    <div className={cn(!readonly ? `${s.gradientBorder}` : 'bg-gray-50', ' relative shadow-md')}>
      <div className='rounded-xl bg-[#EEF4FF]'>
        <div className="flex justify-between items-center h-11 px-3">
          <div className="flex items-center space-x-1">
            <div className='h2'>{mode !== AppType.completion ? t('appDebug.chatSubTitle') : t('appDebug.completionSubTitle')}</div>
            {!readonly && (
              <Tooltip
                htmlContent={<div className='w-[180px]'>
                  {t('appDebug.promptTip')}
                </div>}
                selector='config-prompt-tooltip'>
                <HelpCircle className='w-[14px] h-[14px] text-indigo-400' />
              </Tooltip>
            )}
          </div>
          <div className='flex items-center'>
            {!isAgent && !readonly && (
              <AutomaticBtn onClick={showAutomaticTrue} />
            )}
          </div>
        </div>
        <PromptEditorHeightResizeWrap
          className='px-4 pt-2 min-h-[228px] bg-white rounded-t-xl text-sm text-gray-700'
          height={editorHeight}
          minHeight={minHeight}
          onHeightChange={setEditorHeight}
          footer={(
            <div className='pl-4 pb-2 flex bg-white rounded-b-xl'>
              <div className="h-[18px] leading-[18px] px-1 rounded-md bg-gray-100 text-xs text-gray-500">{promptTemplate.length}</div>
            </div>
          )}
        >
          <PromptEditor
            className='min-h-[210px]'
            compact
            value={promptTemplate}
            contextBlock={{
              show: false,
              selectable: !hasSetBlockStatus.context,
              datasets: dataSets.map(item => ({
                id: item.id,
                name: item.name,
                type: item.data_source_type,
              })),
              onAddContext: showSelectDataSet,
            }}
            variableBlock={{
              show: true,
              variables: modelConfig.configs.prompt_variables.filter(item => item.type !== 'api').map(item => ({
                name: item.name,
                value: item.key,
              })),
            }}
            externalToolBlock={{
              show: true,
              externalTools: modelConfig.configs.prompt_variables.filter(item => item.type === 'api').map(item => ({
                name: item.name,
                variableName: item.key,
                icon: item.icon,
                icon_background: item.icon_background,
              })),
              onAddExternalTool: handleOpenExternalDataToolModal,
            }}
            historyBlock={{
              show: false,
              selectable: false,
              history: {
                user: '',
                assistant: '',
              },
              onEditRole: () => { },
            }}
            queryBlock={{
              show: false,
              selectable: !hasSetBlockStatus.query,
            }}
            onChange={(value) => {
              handleChange?.(value, [])
            }}
            onBlur={() => {
              handleChange(promptTemplate, getVars(promptTemplate))
            }}
          />
        </PromptEditorHeightResizeWrap>
      </div>

      {isShowConfirmAddVar && (
        <ConfirmAddVar
          varNameArr={newPromptVariables.map(v => v.name)}
          onConfrim={handleAutoAdd(true)}
          onCancel={handleAutoAdd(false)}
          onHide={hideConfirmAddVar}
        />
      )}

      {showAutomatic && (
        <GetAutomaticResModal
          mode={mode as AppType}
          isShow={showAutomatic}
          onClose={showAutomaticFalse}
          onFinished={handleAutomaticRes}
        />
      )}
    </div>
  )
}

export default React.memo(Prompt)
