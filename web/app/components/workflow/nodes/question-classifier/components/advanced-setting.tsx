'use client'
import type { FC } from 'react'
import React from 'react'
import { useTranslation } from 'react-i18next'
import MemoryConfig from '../../_base/components/memory-config'
import Editor from '@/app/components/workflow/nodes/_base/components/prompt/editor'
import type { Memory, Node, NodeOutPutVar } from '@/app/components/workflow/types'
import TooltipPlus from '@/app/components/base/tooltip-plus'
import { HelpCircle } from '@/app/components/base/icons/src/vender/line/general'
const i18nPrefix = 'workflow.nodes.questionClassifiers'

type Props = {
  instruction: string
  onInstructionChange: (instruction: string) => void
  hideMemorySetting: boolean
  memory?: Memory
  onMemoryChange: (memory?: Memory) => void
  readonly?: boolean
  isChatModel: boolean
  isChatApp: boolean
  hasSetBlockStatus?: {
    context: boolean
    history: boolean
    query: boolean
  }
  nodesOutputVars: NodeOutPutVar[]
  availableNodes: Node[]
}

const AdvancedSetting: FC<Props> = ({
  instruction,
  onInstructionChange,
  hideMemorySetting,
  memory,
  onMemoryChange,
  readonly,
  isChatModel,
  isChatApp,
  hasSetBlockStatus,
  nodesOutputVars,
  availableNodes,
}) => {
  const { t } = useTranslation()

  return (
    <>
      <Editor
        title={
          <div className='flex items-center space-x-1'>
            <span className='uppercase'>{t(`${i18nPrefix}.instruction`)}</span>
            <TooltipPlus popupContent={
              <div className='w-[120px]'>
                {t(`${i18nPrefix}.instructionTip`)}
              </div>}>
              <HelpCircle className='w-3.5 h-3.5 ml-0.5 text-gray-400' />
            </TooltipPlus>
          </div>
        }
        value={instruction}
        onChange={onInstructionChange}
        readOnly={readonly}
        isChatModel={isChatModel}
        isChatApp={isChatApp}
        isShowContext={false}
        hasSetBlockStatus={hasSetBlockStatus}
        nodesOutputVars={nodesOutputVars}
        availableNodes={availableNodes}
      />
      {!hideMemorySetting && (
        <MemoryConfig
          className='mt-4'
          readonly={false}
          config={{ data: memory }}
          onChange={onMemoryChange}
          canSetRoleName={false}
        />
      )}
    </>
  )
}
export default React.memo(AdvancedSetting)
