'use client'
import React, { useEffect, useRef, useState } from 'react'
import copy from 'copy-to-clipboard'
import { t } from 'i18next'
import s from './style.module.css'
import { randomString } from '@/utils'
import Tooltip from '@/app/components/base/tooltip'

type IInputCopyProps = {
  value?: string
  className?: string
  readOnly?: boolean
  children?: React.ReactNode
}

const InputCopy = ({
  value = '',
  className,
  readOnly = true,
  children,
}: IInputCopyProps) => {
  const [isCopied, setIsCopied] = useState(false)

  const selector = useRef(`input-tooltip-${randomString(4)}`)

  useEffect(() => {
    if (isCopied) {
      const timeout = setTimeout(() => {
        setIsCopied(false)
      }, 1000)

      return () => {
        clearTimeout(timeout)
      }
    }
  }, [isCopied])

  return (
    <div className={`flex rounded-lg bg-gray-50 hover:bg-gray-50 py-2 items-center ${className}`}>
      <div className="flex items-center flex-grow h-5">
        {children}
        <div className='flex-grow bg-gray-50 text-[13px] relative h-full'>
          <Tooltip
            selector={selector.current}
            content={isCopied ? `${t('appApi.copied')}` : `${t('appApi.copy')}`}
            className='z-10'
          >
            <div className='absolute top-0 left-0 w-full pl-2 pr-2 truncate cursor-pointer r-0' onClick={() => {
              copy(value)
              setIsCopied(true)
            }}>{value}</div>
          </Tooltip>
        </div>
        <div className="flex-shrink-0 h-4 bg-gray-200 border" />
        <Tooltip
          selector={selector.current}
          content={isCopied ? `${t('appApi.copied')}` : `${t('appApi.copy')}`}
          className='z-10'
        >
          <div className="px-0.5 flex-shrink-0">
            <div className={`box-border w-[30px] h-[30px] flex items-center justify-center rounded-lg hover:bg-gray-100 cursor-pointer ${s.copyIcon} ${isCopied ? s.copied : ''}`} onClick={() => {
              copy(value)
              setIsCopied(true)
            }}>
            </div>
          </div>
        </Tooltip>
      </div>
    </div>
  )
}

export default InputCopy
