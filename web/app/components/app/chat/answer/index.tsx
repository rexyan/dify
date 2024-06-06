'use client'
import type { FC, ReactNode } from 'react'
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { UserCircleIcon } from '@heroicons/react/24/solid'
import cn from 'classnames'
import type { CitationItem, DisplayScene, FeedbackFunc, Feedbacktype, IChatItem } from '../type'
import OperationBtn from '../operation'
import LoadingAnim from '../loading-anim'
import { RatingIcon } from '../icon-component'
import s from '../style.module.css'
import MoreInfo from '../more-info'
import CopyBtn from '../copy-btn'
import Thought from '../thought'
import Citation from '../citation'
import AudioBtn from '@/app/components/base/audio-btn'
import { randomString } from '@/utils'
import type { MessageRating } from '@/models/log'
import Tooltip from '@/app/components/base/tooltip'
import { Markdown } from '@/app/components/base/markdown'
import type { DataSet } from '@/models/datasets'
import AnnotationCtrlBtn from '@/app/components/app/configuration/toolbox/annotation/annotation-ctrl-btn'
import EditReplyModal from '@/app/components/app/annotation/edit-annotation-modal'
import { EditTitle } from '@/app/components/app/annotation/edit-annotation-modal/edit-item'
import { MessageFast } from '@/app/components/base/icons/src/vender/solid/communication'
import type { Emoji } from '@/app/components/tools/types'
import type { VisionFile } from '@/types/app'
import ImageGallery from '@/app/components/base/image-gallery'
import Log from '@/app/components/app/chat/log'

const IconWrapper: FC<{ children: React.ReactNode | string }> = ({ children }) => {
  return <div className={'rounded-lg h-6 w-6 flex items-center justify-center hover:bg-gray-100'}>
    {children}
  </div>
}
export type IAnswerProps = {
  item: IChatItem
  index: number
  feedbackDisabled: boolean
  isHideFeedbackEdit: boolean
  onQueryChange: (query: string) => void
  onFeedback?: FeedbackFunc
  displayScene: DisplayScene
  isResponding?: boolean
  answerIcon?: ReactNode
  citation?: CitationItem[]
  dataSets?: DataSet[]
  isShowCitation?: boolean
  isShowCitationHitInfo?: boolean
  isShowTextToSpeech?: boolean
  // Annotation props
  supportAnnotation?: boolean
  appId?: string
  question: string
  onAnnotationEdited?: (question: string, answer: string, index: number) => void
  onAnnotationAdded?: (annotationId: string, authorName: string, question: string, answer: string, index: number) => void
  onAnnotationRemoved?: (index: number) => void
  allToolIcons?: Record<string, string | Emoji>
  isShowPromptLog?: boolean
}
// The component needs to maintain its own state to control whether to display input component
const Answer: FC<IAnswerProps> = ({
  item,
  index,
  onQueryChange,
  feedbackDisabled = false,
  isHideFeedbackEdit = false,
  onFeedback,
  displayScene = 'web',
  isResponding,
  answerIcon,
  citation,
  isShowCitation,
  isShowCitationHitInfo = false,
  isShowTextToSpeech,
  supportAnnotation,
  appId,
  question,
  onAnnotationEdited,
  onAnnotationAdded,
  onAnnotationRemoved,
  allToolIcons,
  isShowPromptLog,
}) => {
  const { id, content, more, feedback, adminFeedback, annotation, agent_thoughts } = item
  const isAgentMode = !!agent_thoughts && agent_thoughts.length > 0
  const hasAnnotation = useMemo(() => !!annotation, [annotation])
  // const [annotation, setAnnotation] = useState<Annotation | undefined | null>(initAnnotation)
  // const [inputValue, setInputValue] = useState<string>(initAnnotation?.content ?? '')
  const [localAdminFeedback, setLocalAdminFeedback] = useState<Feedbacktype | undefined | null>(adminFeedback)
  // const { userProfile } = useContext(AppContext)
  const { t } = useTranslation()

  const [isShowReplyModal, setIsShowReplyModal] = useState(false)

  /**
 * Render feedback results (distinguish between users and administrators)
 * User reviews cannot be cancelled in Console
 * @param rating feedback result
 * @param isUserFeedback Whether it is user's feedback
 * @param isWebScene Whether it is web scene
 * @returns comp
 */
  const renderFeedbackRating = (rating: MessageRating | undefined, isUserFeedback = true, isWebScene = true) => {
    if (!rating)
      return null

    const isLike = rating === 'like'
    const ratingIconClassname = isLike ? 'text-primary-600 bg-primary-100 hover:bg-primary-200' : 'text-red-600 bg-red-100 hover:bg-red-200'
    const UserSymbol = <UserCircleIcon className='absolute top-[-2px] left-[18px] w-3 h-3 rounded-lg text-gray-400 bg-white' />
    // The tooltip is always displayed, but the content is different for different scenarios.
    return (
      <Tooltip
        selector={`user-feedback-${randomString(16)}`}
        content={((isWebScene || (!isUserFeedback && !isWebScene)) ? isLike ? t('appDebug.operation.cancelAgree') : t('appDebug.operation.cancelDisagree') : (!isWebScene && isUserFeedback) ? `${t('appDebug.operation.userAction')}${isLike ? t('appDebug.operation.agree') : t('appDebug.operation.disagree')}` : '') as string}
      >
        <div
          className={`relative box-border flex items-center justify-center h-7 w-7 p-0.5 rounded-lg bg-white cursor-pointer text-gray-500 hover:text-gray-800 ${(!isWebScene && isUserFeedback) ? '!cursor-default' : ''}`}
          style={{ boxShadow: '0px 4px 6px -1px rgba(0, 0, 0, 0.1), 0px 2px 4px -2px rgba(0, 0, 0, 0.05)' }}
          {...((isWebScene || (!isUserFeedback && !isWebScene))
            ? {
              onClick: async () => {
                const res = await onFeedback?.(id, { rating: null })
                if (res && !isWebScene)
                  setLocalAdminFeedback({ rating: null })
              },
            }
            : {})}
        >
          <div className={`${ratingIconClassname} rounded-lg h-6 w-6 flex items-center justify-center`}>
            <RatingIcon isLike={isLike} />
          </div>
          {!isWebScene && isUserFeedback && UserSymbol}
        </div>
      </Tooltip>
    )
  }

  /**
   * Different scenarios have different operation items.
   * @param isWebScene  Whether it is web scene
   * @returns comp
   */
  const renderItemOperation = (isWebScene = true) => {
    const userOperation = () => {
      return feedback?.rating
        ? null
        : <div className='flex gap-1'>
          <Tooltip selector={`user-feedback-${randomString(16)}`} content={t('appLog.detail.operation.like') as string}>
            {OperationBtn({ innerContent: <IconWrapper><RatingIcon isLike={true} /></IconWrapper>, onClick: () => onFeedback?.(id, { rating: 'like' }) })}
          </Tooltip>
          <Tooltip selector={`user-feedback-${randomString(16)}`} content={t('appLog.detail.operation.dislike') as string}>
            {OperationBtn({ innerContent: <IconWrapper><RatingIcon isLike={false} /></IconWrapper>, onClick: () => onFeedback?.(id, { rating: 'dislike' }) })}
          </Tooltip>
        </div>
    }

    const adminOperation = () => {
      return <div className='flex gap-1'>
        {!localAdminFeedback?.rating && <>
          <Tooltip selector={`user-feedback-${randomString(16)}`} content={t('appLog.detail.operation.like') as string}>
            {OperationBtn({
              innerContent: <IconWrapper><RatingIcon isLike={true} /></IconWrapper>,
              onClick: async () => {
                const res = await onFeedback?.(id, { rating: 'like' })
                if (res)
                  setLocalAdminFeedback({ rating: 'like' })
              },
            })}
          </Tooltip>
          <Tooltip selector={`user-feedback-${randomString(16)}`} content={t('appLog.detail.operation.dislike') as string}>
            {OperationBtn({
              innerContent: <IconWrapper><RatingIcon isLike={false} /></IconWrapper>,
              onClick: async () => {
                const res = await onFeedback?.(id, { rating: 'dislike' })
                if (res)
                  setLocalAdminFeedback({ rating: 'dislike' })
              },
            })}
          </Tooltip>
        </>}
      </div>
    }

    return (
      <div className={`${s.itemOperation} flex gap-2`}>
        {isWebScene ? userOperation() : adminOperation()}
      </div>
    )
  }

  const getImgs = (list?: VisionFile[]) => {
    if (!list)
      return []
    return list.filter(file => file.type === 'image' && file.belongs_to === 'assistant')
  }

  const agentModeAnswer = (
    <div>
      {agent_thoughts?.map((item, index) => (
        <div key={index}>
          {item.thought && (
            <Markdown content={item.thought} />
          )}
          {/* {item.tool} */}
          {/* perhaps not use tool */}
          {!!item.tool && (
            <Thought
              thought={item}
              allToolIcons={allToolIcons || {}}
              isFinished={!!item.observation || !isResponding}
            />
          )}

          {getImgs(item.message_files).length > 0 && (
            <ImageGallery srcs={getImgs(item.message_files).map(item => item.url)} />
          )}
        </div>
      ))}
    </div>
  )

  const [containerWidth, setContainerWidth] = useState(0)
  const [contentWidth, setContentWidth] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  const getContainerWidth = () => {
    if (containerRef.current)
      setContainerWidth(containerRef.current?.clientWidth + 24)
  }
  const getContentWidth = () => {
    if (contentRef.current)
      setContentWidth(contentRef.current?.clientWidth)
  }

  useEffect(() => {
    getContainerWidth()
  }, [])

  useEffect(() => {
    if (!isResponding)
      getContentWidth()
  }, [isResponding])

  const operationWidth = useMemo(() => {
    let width = 0
    if (!item.isOpeningStatement)
      width += 28
    if (!item.isOpeningStatement && isShowPromptLog)
      width += 102 + 8
    if (!item.isOpeningStatement && isShowTextToSpeech)
      width += 33
    if (!item.isOpeningStatement && supportAnnotation)
      width += 96 + 8
    if (!feedbackDisabled && !item.feedbackDisabled)
      width += 60 + 8
    if (!feedbackDisabled && localAdminFeedback?.rating && !item.isOpeningStatement)
      width += 60 + 8
    if (!feedbackDisabled && feedback?.rating && !item.isOpeningStatement)
      width += 28 + 8
    return width
  }, [item.isOpeningStatement, item.feedbackDisabled, isShowPromptLog, isShowTextToSpeech, supportAnnotation, feedbackDisabled, localAdminFeedback?.rating, feedback?.rating])

  const positionRight = useMemo(() => operationWidth < containerWidth - contentWidth - 4, [operationWidth, containerWidth, contentWidth])

  return (
    // data-id for debug the item message is right
    <div key={id} data-id={id}>
      <div className='flex items-start'>
        {
          answerIcon || (
            <div className={`${s.answerIcon} w-10 h-10 shrink-0`}>
              {isResponding
                && <div className={s.typeingIcon}>
                  <LoadingAnim type='avatar' />
                </div>
              }
            </div>
          )
        }
        <div ref={containerRef} className={cn(s.answerWrapWrap, 'chat-answer-container')}>
          <div className={cn(s.answerWrap, 'group')}>
            <div ref={contentRef} className={`${s.answer} relative text-sm text-gray-900`}>
              <div className={'ml-2 py-3 px-4 bg-gray-100 rounded-tr-2xl rounded-b-2xl'}>
                {(isResponding && (isAgentMode ? (!content && (agent_thoughts || []).filter(item => !!item.thought || !!item.tool).length === 0) : !content))
                  ? (
                    <div className='flex items-center justify-center w-6 h-5'>
                      <LoadingAnim type='text' />
                    </div>
                  )
                  : (
                    <div>
                      {annotation?.logAnnotation && (
                        <div className='mb-1'>
                          <div className='mb-3'>
                            {isAgentMode
                              ? (<div className='line-through !text-gray-400'>{agentModeAnswer}</div>)
                              : (
                                <Markdown className='line-through !text-gray-400' content={content} />
                              )}
                          </div>
                          <EditTitle title={t('appAnnotation.editBy', {
                            author: annotation?.logAnnotation.account?.name,
                          })} />
                        </div>
                      )}
                      <div>
                        {annotation?.logAnnotation
                          ? (
                            <Markdown content={annotation?.logAnnotation.content || ''} />
                          )
                          : (isAgentMode
                            ? agentModeAnswer
                            : (
                              <Markdown content={content} />
                            ))}
                      </div>
                      {(hasAnnotation && !annotation?.logAnnotation) && (
                        <EditTitle className='mt-1' title={t('appAnnotation.editBy', {
                          author: annotation?.authorName,
                        })} />
                      )}
                      {item.isOpeningStatement && item.suggestedQuestions && item.suggestedQuestions.filter(q => !!q && q.trim()).length > 0 && (
                        <div className='flex flex-wrap'>
                          {item.suggestedQuestions.filter(q => !!q && q.trim()).map((question, index) => (
                            <div
                              key={index}
                              className='mt-1 mr-1 max-w-full last:mr-0 shrink-0 py-[5px] leading-[18px] items-center px-4 rounded-lg border border-gray-200 shadow-xs bg-white text-xs font-medium text-primary-600 cursor-pointer'
                              onClick={() => onQueryChange(question)}
                            >
                              {question}
                            </div>),
                          )}
                        </div>
                      )}
                    </div>
                  )}
                {
                  !!citation?.length && isShowCitation && !isResponding && (
                    <Citation data={citation} showHitInfo={isShowCitationHitInfo} />
                  )
                }
              </div>
              {hasAnnotation && (
                <div
                  className={cn(s.hasAnnotationBtn, 'absolute -top-3.5 -right-3.5 box-border flex items-center justify-center h-7 w-7 p-0.5 rounded-lg bg-white cursor-pointer text-[#444CE7]')}
                  style={{ boxShadow: '0px 4px 6px -1px rgba(0, 0, 0, 0.1), 0px 2px 4px -2px rgba(0, 0, 0, 0.05)' }}
                >
                  <div className='p-1 rounded-lg bg-[#EEF4FF] '>
                    <MessageFast className='w-4 h-4' />
                  </div>
                </div>
              )}
              <div
                className={cn(
                  'absolute -top-3.5 flex justify-end gap-1',
                  positionRight ? '!top-[9px]' : '-right-3.5',
                )}
                style={positionRight ? { left: contentWidth + 8 } : {}}
              >
                {!item.isOpeningStatement && (
                  <CopyBtn
                    value={content}
                    className={cn(s.copyBtn, 'mr-1')}
                  />
                )}
                {((isShowPromptLog && !isResponding) || (!item.isOpeningStatement && isShowTextToSpeech)) && (
                  <div className='hidden group-hover:flex items-center w-max h-[28px] p-0.5 rounded-lg bg-white border-[0.5px] border-gray-100 shadow-md shrink-0'>
                    {isShowPromptLog && !isResponding && (
                      <Log logItem={item} />
                    )}
                    {!item.isOpeningStatement && isShowTextToSpeech && (
                      <>
                        <div className='mx-1 w-[1px] h-[14px] bg-gray-200'/>
                        <AudioBtn
                          value={content}
                          noCache={false}
                          className={cn(s.playBtn)}
                        />
                      </>
                    )}
                  </div>
                )}
                {(!item.isOpeningStatement && supportAnnotation) && (
                  <AnnotationCtrlBtn
                    appId={appId!}
                    messageId={id}
                    annotationId={annotation?.id || ''}
                    className={cn(s.annotationBtn, 'ml-1 shrink-0')}
                    cached={hasAnnotation}
                    query={question}
                    answer={content}
                    onAdded={(id, authorName) => onAnnotationAdded?.(id, authorName, question, content, index)}
                    onEdit={() => setIsShowReplyModal(true)}
                    onRemoved={() => onAnnotationRemoved!(index)}
                  />
                )}

                <EditReplyModal
                  isShow={isShowReplyModal}
                  onHide={() => setIsShowReplyModal(false)}
                  query={question}
                  answer={content}
                  onEdited={(editedQuery, editedAnswer) => onAnnotationEdited!(editedQuery, editedAnswer, index)}
                  onAdded={(annotationId, authorName, editedQuery, editedAnswer) => onAnnotationAdded!(annotationId, authorName, editedQuery, editedAnswer, index)}
                  appId={appId!}
                  messageId={id}
                  annotationId={annotation?.id || ''}
                  createdAt={annotation?.created_at}
                  onRemove={() => { }}
                />

                {!feedbackDisabled && !item.feedbackDisabled && renderItemOperation(displayScene !== 'console')}
                {/* Admin feedback is displayed only in the background. */}
                {!feedbackDisabled && renderFeedbackRating(localAdminFeedback?.rating, false, false)}
                {/* User feedback must be displayed */}
                {!feedbackDisabled && renderFeedbackRating(feedback?.rating, !isHideFeedbackEdit, displayScene !== 'console')}
              </div>
            </div>
            {more && <MoreInfo className='invisible group-hover:visible' more={more} isQuestion={false} />}
          </div>
        </div>
      </div>
    </div>
  )
}
export default React.memo(Answer)
